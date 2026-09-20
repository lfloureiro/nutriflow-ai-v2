import { describe, expect, it } from "vitest";

import type { FamilyMealPlan } from "./api/mealPlanTypes";
import type { ShoppingList } from "./api/pantryShoppingTypes";
import type {
  SharedWeeklyPlanChoice,
  SharedWeeklyPlanProposalRequest,
} from "./api/weeklyPlanningTypes";
import {
  weeklyPlanRequest,
  proposalHasOnlySkippedSlots,
  addCalendarDays,
  isWeekendDate,
  mealEntryFor,
  weeklySourcesFor,
  weeklySkippedSlotMessages,
  shoppingRefreshSummary,
  nutritionPlanAuthorityLabel,
  formatMealPortion,
  formatMealEnergyReference,
  weeklyExplanationLabel,
  weeklyExplanationLabels,
  nutritionSummaryRows,
  formatPlanRuleTarget,
  planRuleStatusLabel,
  numericPlanComparisonRules,
  adaptationKindLabel,
  pinnedChoiceForAdaptation,
  pinnedChoiceForOriginal,
  upsertPinnedWeeklyChoice,
  transformationLimitationLabel,
} from "./WeeklyProposalPreview";

describe("weekly proposal calendar dates", () => {
  it("walks a Monday-Sunday week without timezone drift", () => {
    expect(addCalendarDays("2026-09-14", 0)).toBe("2026-09-14");
    expect(addCalendarDays("2026-09-14", 6)).toBe("2026-09-20");
  });

  it("crosses month boundaries", () => {
    expect(addCalendarDays("2026-09-28", 6)).toBe("2026-10-04");
  });
});

describe("weekly meal source policy", () => {
  it("keeps breakfast and snacks at home", () => {
    expect(weeklySourcesFor("2026-09-15", "breakfast")).toEqual(["cooked"]);
    expect(weeklySourcesFor("2026-09-15", "snack")).toEqual(["cooked"]);
  });

  it("uses delivery fallback for weekday lunch rather than another cooked meal", () => {
    expect(isWeekendDate("2026-09-15")).toBe(false);
    expect(weeklySourcesFor("2026-09-15", "lunch")).toEqual([
      "uber_eats",
      "glovo",
    ]);
  });

  it("uses home or restaurant for weekend lunch and dinner", () => {
    expect(isWeekendDate("2026-09-19")).toBe(true);
    expect(weeklySourcesFor("2026-09-19", "lunch")).toEqual([
      "cooked",
      "restaurant",
    ]);
    expect(weeklySourcesFor("2026-09-20", "dinner")).toEqual([
      "cooked",
      "restaurant",
    ]);
  });

  it("keeps weekday dinner as a home-cooked family meal", () => {
    expect(weeklySourcesFor("2026-09-17", "dinner")).toEqual(["cooked"]);
  });
});

describe("weekly no-plan diagnostics", () => {
  it("distinguishes all-skipped slots from a searched but infeasible week", () => {
    expect(
      proposalHasOnlySkippedSlots({
        family_id: "family",
        participant_ids: ["person-1", "person-2"],
        week_start: "2026-09-14",
        week_end: "2026-09-20",
        engine_version: "test",
        slot_engine_versions: {},
        selected_plan: null,
        skipped_slots: [
          {
            slot_key: "2026-09-14:lunch",
            planning_date: "2026-09-14",
            meal_type: "lunch",
            reason: "no_eligible_candidates",
            exclusion_reasons: ["candidate_unavailable"],
          },
        ],
        evaluated_combinations: 0,
        feasible_combinations: 0,
        rejected_by_person_weekly_maximum: 0,
        rejected_by_person_daily_limit: 0,
        search_strategy: "bounded",
        search_space_size: 0,
        search_truncated: false,
      }),
    ).toBe(true);
  });

  it("keeps a genuine searched infeasibility separate", () => {
    expect(
      proposalHasOnlySkippedSlots({
        family_id: "family",
        participant_ids: ["person-1", "person-2"],
        week_start: "2026-09-14",
        week_end: "2026-09-20",
        engine_version: "test",
        slot_engine_versions: {},
        selected_plan: null,
        skipped_slots: [],
        evaluated_combinations: 12,
        feasible_combinations: 0,
        rejected_by_person_weekly_maximum: 12,
        rejected_by_person_daily_limit: 0,
        search_strategy: "exact",
        search_space_size: 12,
        search_truncated: false,
      }),
    ).toBe(false);
  });
});


describe("server-authoritative unavailable weekly slots", () => {
  it("keeps an unavailable weekday delivery lunch visibly pending", () => {
    expect(
      weeklySkippedSlotMessages(
        [
          {
            slot_key: "2026-09-15:lunch",
            planning_date: "2026-09-15",
            meal_type: "lunch",
            reason: "no_eligible_candidates",
            exclusion_reasons: ["candidate_unavailable"],
          },
        ],
        "pt-PT",
      ),
    ).toEqual({
      "2026-09-15:lunch":
        "Almoço de dia útil: primeiro devem ser usadas sobras reais do jantar anterior; sem sobras, só entra uma opção Uber Eats/Glovo com disponibilidade conhecida. Ainda não existe uma opção automática segura para este slot.",
    });
  });
});

describe("weekly portion labels", () => {
  it("formats recipe servings without raw database precision", () => {
    expect(formatMealPortion("2.0000", "serving", "1966.33", "pt-PT")).toBe(
      "2 porções da receita · ~1966 kcal",
    );
    expect(formatMealPortion("0.7500", "serving", "737.38", "pt-PT")).toBe(
      "0,75 porção da receita · ~737 kcal",
    );
  });

  it("keeps physical units compact", () => {
    expect(formatMealPortion("250.0000", "g", "520.40", "pt-PT")).toBe(
      "250 g · ~520 kcal",
    );
  });
});


describe("weekly participant detail formatting", () => {
  it("shows a readable meal energy reference", () => {
    expect(formatMealEnergyReference("540.00", "600.00", "pt-PT")).toBe(
      "540–600 kcal",
    );
    expect(formatMealEnergyReference(null, "700.00", "pt-PT")).toBe("≤ 700 kcal");
  });

  it("hides duplicate Plan-Fit machine codes", () => {
    expect(weeklyExplanationLabel("plan_fit_status:unknown", "pt-PT")).toBeNull();
    expect(weeklyExplanationLabel("plan_fit_score_unavailable", "pt-PT")).toBeNull();
  });

  it("translates preference and planning evidence", () => {
    expect(
      weeklyExplanationLabels(
        [
          "rated:recipe:legacy-v1:recipe:4:4",
          "planning_location:Casa",
          "plan_fit_status:unknown",
        ],
        "pt-PT",
      ),
    ).toEqual([
      "Avaliação pessoal desta receita: 4/5.",
      "Local de preparação: Casa.",
    ]);
  });
});


describe("weekly nutrition comparison", () => {
  it("formats a compact nutrition summary with priority nutrients", () => {
    expect(
      nutritionSummaryRows(
        {
          energy_kcal: "620.40",
          nutrients: {
            sodium: { value: "450", unit: "mg" },
            fiber: { value: "8.2", unit: "g" },
            protein: { value: "42.6", unit: "g" },
            carbohydrate: { value: "54.1", unit: "g" },
            fat: { value: "21.3", unit: "g" },
          },
        },
        "pt-PT",
      ),
    ).toEqual([
      { key: "energy", label: "Energia", value: "620,4 kcal" },
      { key: "protein", label: "Proteína", value: "42,6 g" },
      { key: "carbohydrate", label: "Hidratos de carbono", value: "54,1 g" },
      { key: "fat", label: "Gordura", value: "21,3 g" },
      { key: "fiber", label: "Fibra", value: "8,2 g" },
      { key: "sodium", label: "Sódio", value: "450 mg" },
    ]);
  });

  it("formats plan targets and keeps only numeric nutrient comparisons", () => {
    const numericRule = {
      rule_id: "protein",
      target_type: "nutrient",
      target_key: "protein",
      operator: "range",
      scope: "meal" as const,
      status: "pass" as const,
      is_mandatory: true,
      priority: 100,
      observed_value: "42.6",
      observed_unit: "g",
      projected_daily_value: null,
      target_min: "40",
      target_max: "50",
      target_value: null,
      target_unit: "g",
      score: "1",
      explanation: "test",
      source: {
        plan_id: "plan",
        plan_title: "Plano",
        plan_source_type: "nutritionist",
        source_name: null,
        source_reference: null,
        rule_source: "nutritionist",
      },
    };
    const qualitativeRule = {
      ...numericRule,
      rule_id: "vegetables",
      target_type: "meal_composition",
      target_key: "leafy_vegetables",
      observed_value: null,
      target_min: null,
      target_max: null,
      score: null,
      status: "not_evaluated" as const,
    };

    expect(formatPlanRuleTarget(numericRule, "pt-PT")).toBe("40–50 g");
    expect(planRuleStatusLabel("pass", "pt-PT")).toBe("Dentro do alvo");
    expect(numericPlanComparisonRules([numericRule, qualitativeRule])).toEqual([
      numericRule,
    ]);
  });

  it("labels an adaptation according to its purpose", () => {
    expect(
      adaptationKindLabel(
        {
          kind: "plan_adapted",
          operation: {
            operation_type: "replace_ingredient",
            substitution_group: "dairy",
            recipe_ingredient_id: "ingredient",
            source_food_item_id: "source",
            source_food_name: "Natas",
            source_quantity: "100",
            source_unit: "g",
            replacement_food_item_id: "replacement",
            replacement_food_name: "Iogurte",
            replacement_quantity: "100",
            replacement_unit: "g",
          },
          participant_results: [],
          plan_improvement_participants: 1,
          preference_improvement_participants: 0,
          minimum_plan_score_delta: "0.1",
          average_plan_score_delta: "0.1",
          minimum_preference_delta: "0",
          average_preference_delta: "0",
          explanation: [],
        },
        "pt-PT",
      ),
    ).toBe("Melhora o plano");
  });
});


describe("weekly transformation limitations", () => {
  it("translates missing structured substitution profiles", () => {
    expect(
      transformationLimitationLabel(
        "no_structured_substitution_profiles",
        "pt-PT",
      ),
    ).toContain("substituições estruturadas");
  });

  it("does not leak unknown machine limitations", () => {
    expect(transformationLimitationLabel("internal:unknown", "pt-PT")).toBeNull();
  });
});


describe("weekly NutritionPlan authority labels", () => {
  it("distinguishes active, partial and absent plan coverage", () => {
    expect(nutritionPlanAuthorityLabel("active_plan", "pt-PT")).toBe("Activo");
    expect(nutritionPlanAuthorityLabel("partial_plan_coverage", "pt-PT")).toBe(
      "Cobertura parcial",
    );
    expect(nutritionPlanAuthorityLabel("no_active_plan", "pt-PT")).toBe(
      "Sem plano activo",
    );
    expect(nutritionPlanAuthorityLabel("plan_conflict", "en")).toBe("Plan conflict");
  });
});


describe("weekly matrix plan overlay", () => {
  const plan: FamilyMealPlan = {
    family_id: "family",
    family_name: "Demo",
    timezone: "Europe/Lisbon",
    start_date: "2026-09-14",
    end_date: "2026-09-20",
    days: [
      {
        date: "2026-09-14",
        slots: [
          {
            meal_type: "lunch",
            meals: [
              {
                id: "meal-1",
                meal_type: "lunch",
                title: null,
                scheduled_at: "2026-09-14T12:00:00Z",
                local_time: "13:00:00",
                status: "planned",
                recipe_id: "recipe-1",
                recipe_name: "Salmão com legumes",
                location: "Casa",
                notes: null,
                transformations: [],
                participants: [],
              },
            ],
          },
          { meal_type: "snack", meals: [] },
        ],
      },
    ],
  };

  it("returns the existing meal for its matrix cell", () => {
    expect(mealEntryFor(plan, "2026-09-14", "lunch")?.recipe_name).toBe(
      "Salmão com legumes",
    );
  });

  it("keeps an empty matrix cell empty", () => {
    expect(mealEntryFor(plan, "2026-09-14", "snack")).toBeNull();
  });
});


describe("weekly application identity", () => {
  const proposal: SharedWeeklyPlanProposalRequest = {
    person_ids: ["person-1", "person-2"],
    slots: [],
    max_combinations: 256,
  };

  const baseChoice: SharedWeeklyPlanChoice = {
    slot_key: "2026-09-15:breakfast",
    planning_date: "2026-09-15",
    scheduled_at: "2026-09-15T08:30:00Z",
    meal_type: "breakfast",
    candidate_key: "recipe:breakfast",
    candidate_name: "Pequeno-almoço",
    candidate_kind: "recipe",
    recipe_id: "recipe-id",
    minimum_score: "0.8",
    average_score: "0.9",
    participants: [],
    transformation: null,
  };

  it("builds and replaces an exact adaptation pin for one weekly slot", () => {
    const adaptation = {
      kind: "plan_adapted" as const,
      operation: {
        operation_type: "replace_ingredient" as const,
        substitution_group: "dairy",
        recipe_ingredient_id: "ingredient-id",
        source_food_item_id: "source-id",
        source_food_name: "Natas",
        source_quantity: "100",
        source_unit: "g",
        replacement_food_item_id: "replacement-id",
        replacement_food_name: "Iogurte",
        replacement_quantity: "100",
        replacement_unit: "g",
      },
      participant_results: [],
      plan_improvement_participants: 1,
      preference_improvement_participants: 0,
      minimum_plan_score_delta: "0.1",
      average_plan_score_delta: "0.1",
      minimum_preference_delta: "0",
      average_preference_delta: "0",
      explanation: [],
    };

    const adaptedPin = pinnedChoiceForAdaptation(baseChoice, adaptation);
    expect(adaptedPin).toEqual({
      slot_key: baseChoice.slot_key,
      candidate_key: baseChoice.candidate_key,
      recipe_ingredient_id: "ingredient-id",
      replacement_food_item_id: "replacement-id",
    });

    expect(
      upsertPinnedWeeklyChoice(
        [
          {
            slot_key: baseChoice.slot_key,
            candidate_key: baseChoice.candidate_key,
          },
        ],
        adaptedPin,
      ),
    ).toEqual([adaptedPin]);
  });

  it("can pin the original recipe after reviewing an adapted variant", () => {
    expect(pinnedChoiceForOriginal(baseChoice)).toEqual({
      slot_key: baseChoice.slot_key,
      candidate_key: baseChoice.candidate_key,
    });
  });

  it("pins every reviewed base candidate by slot", () => {
    expect(weeklyPlanRequest(proposal, [baseChoice])).toEqual({
      ...proposal,
      expected_choices: [
        {
          slot_key: baseChoice.slot_key,
          candidate_key: baseChoice.candidate_key,
        },
      ],
    });
  });

  it("pins the exact reviewed ingredient replacement for adapted recipes", () => {
    const transformed: SharedWeeklyPlanChoice = {
      ...baseChoice,
      slot_key: "2026-09-16:breakfast",
      planning_date: "2026-09-16",
      transformation: {
        kind: "plan_adapted",
        recipe_id: "recipe-id",
        operation: {
          operation_type: "replace_ingredient",
          substitution_group: "yogurt",
          recipe_ingredient_id: "ingredient-id",
          source_food_item_id: "source-id",
          source_food_name: "Iogurte natural",
          source_quantity: "150",
          source_unit: "g",
          replacement_food_item_id: "replacement-id",
          replacement_food_name: "Iogurte grego",
          replacement_quantity: "150",
          replacement_unit: "g",
        },
        plan_improvement_participants: 1,
        preference_improvement_participants: 0,
        explanation: ["plan_backed_family_improvement"],
      },
    };

    expect(weeklyPlanRequest(proposal, [baseChoice, transformed])).toEqual({
      ...proposal,
      expected_choices: [
        {
          slot_key: baseChoice.slot_key,
          candidate_key: baseChoice.candidate_key,
        },
        {
          slot_key: transformed.slot_key,
          candidate_key: transformed.candidate_key,
          recipe_ingredient_id: "ingredient-id",
          replacement_food_item_id: "replacement-id",
        },
      ],
    });
  });
});


describe("weekly shopping refresh summary", () => {
  const list: ShoppingList = {
    id: "shopping-list",
    family_id: "family",
    title: "Compras",
    status: "active",
    planning_start: "2026-09-14",
    planning_end: "2026-09-20",
    generated_at: "2026-09-14T08:00:00Z",
    requirements: [],
    planning_issues: ["Recipe missing safe yield evidence"],
    items: [
      {
        id: "auto-needed",
        food_item_id: "food-1",
        name: "Espinafres",
        quantity: "300",
        unit: "g",
        item_source: "automatic",
        status: "needed",
        notes: null,
        sort_order: 0,
      },
      {
        id: "auto-purchased",
        food_item_id: "food-2",
        name: "Tomate",
        quantity: "500",
        unit: "g",
        item_source: "automatic",
        status: "purchased",
        notes: null,
        sort_order: 1,
      },
      {
        id: "manual-needed",
        food_item_id: null,
        name: "Guardanapos",
        quantity: null,
        unit: null,
        item_source: "manual",
        status: "needed",
        notes: null,
        sort_order: 10000,
      },
    ],
    created_at: "2026-09-14T08:00:00Z",
    updated_at: "2026-09-14T08:00:00Z",
  };

  it("counts only automatic ingredients that are still needed", () => {
    expect(shoppingRefreshSummary(list)).toEqual({
      automaticNeeded: 1,
      planningIssues: 1,
    });
  });

  it("reports zero when all automatic requirements are already covered", () => {
    expect(
      shoppingRefreshSummary({
        ...list,
        planning_issues: [],
        items: list.items.map((item) =>
          item.item_source === "automatic" ? { ...item, status: "purchased" as const } : item,
        ),
      }),
    ).toEqual({
      automaticNeeded: 0,
      planningIssues: 0,
    });
  });
});
