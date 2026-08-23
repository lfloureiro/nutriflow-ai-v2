import type { Person, PlanningDailyNutritionState } from "./api/types";

export type RecommendationNutritionBudget = {
  personId: string;
  personName: string;
  consumedKcal: number;
  plannedKcal: number;
  targetMinKcal: number | null;
  targetMaxKcal: number | null;
  remainingMinKcal: number | null;
  remainingMaxKcal: number | null;
};

function numberOrZero(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function optionalNumber(value: string | null): number | null {
  if (value === null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function recommendationNutritionBudget(
  person: Person,
  state: PlanningDailyNutritionState,
): RecommendationNutritionBudget {
  const consumedKcal = numberOrZero(state.energy_consumed_kcal);
  const plannedKcal = numberOrZero(state.energy_planned_kcal);
  const spentKcal = consumedKcal + plannedKcal;
  const remainingMinKcal = optionalNumber(state.energy_remaining_min_kcal);
  const remainingMaxKcal = optionalNumber(state.energy_remaining_max_kcal);

  return {
    personId: person.id,
    personName: [person.first_name, person.last_name].filter(Boolean).join(" "),
    consumedKcal,
    plannedKcal,
    targetMinKcal: remainingMinKcal === null ? null : spentKcal + remainingMinKcal,
    targetMaxKcal: remainingMaxKcal === null ? null : spentKcal + remainingMaxKcal,
    remainingMinKcal,
    remainingMaxKcal,
  };
}

export function budgetProgress(budget: RecommendationNutritionBudget): number | null {
  const target =
    budget.targetMinKcal !== null && budget.targetMaxKcal !== null
      ? (budget.targetMinKcal + budget.targetMaxKcal) / 2
      : budget.targetMaxKcal ?? budget.targetMinKcal;
  if (target === null || target <= 0) return null;
  return Math.max(0, Math.min(1, (budget.consumedKcal + budget.plannedKcal) / target));
}
