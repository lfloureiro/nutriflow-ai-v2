import { describe, expect, it } from "vitest";

import type { Person, PlanningDailyNutritionState } from "./api/types";
import { budgetProgress, recommendationNutritionBudget } from "./recommendationNutrition";

const person: Person = {
  id: "person-1",
  family_id: "family-1",
  first_name: "Pessoa",
  last_name: "Demo",
  birth_date: null,
  preferred_locale: "pt-PT",
  timezone: "Europe/Lisbon",
  created_at: "2026-08-23T00:00:00Z",
  updated_at: "2026-08-23T00:00:00Z",
};

const state: PlanningDailyNutritionState = {
  id: "state-1",
  state_date: "2026-08-23",
  timezone: "Europe/Lisbon",
  energy_consumed_kcal: "1000.00",
  energy_planned_kcal: "200.00",
  energy_remaining_min_kcal: "600.00",
  energy_remaining_max_kcal: "800.00",
  calculation_version: "test",
  computed_at: "2026-08-23T09:00:00Z",
  components: [],
};

describe("recommendationNutritionBudget", () => {
  it("derives the daily target from spent and remaining energy", () => {
    const budget = recommendationNutritionBudget(person, state);

    expect(budget.personName).toBe("Pessoa Demo");
    expect(budget.targetMinKcal).toBe(1800);
    expect(budget.targetMaxKcal).toBe(2000);
    expect(budget.consumedKcal).toBe(1000);
    expect(budget.plannedKcal).toBe(200);
    expect(budget.remainingMinKcal).toBe(600);
    expect(budget.remainingMaxKcal).toBe(800);
  });

  it("calculates bounded progress against the target midpoint", () => {
    const budget = recommendationNutritionBudget(person, state);
    expect(budgetProgress(budget)).toBeCloseTo(1200 / 1900);
  });
});
