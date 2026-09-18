import { describe, expect, it } from "vitest";

import type { FamilyMealPlan } from "./api/mealPlanTypes";
import type {
  SharedWeeklyPlanChoice,
  SharedWeeklyPlanProposalRequest,
} from "./api/weeklyPlanningTypes";
import {
  weeklyPlanRequest,
  addCalendarDays,
  isWeekendDate,
  mealEntryFor,
  weeklySourcesFor,
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
    minimum_score: "0.8",
    average_score: "0.9",
    participants: [],
    transformation: null,
  };

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
