import { ApiError, buildApiUrl } from "./client";
import type {
  EffectiveNutritionPlan,
  NutritionPlanAuthorityState,
  NutritionPlanSummary,
} from "./planFitTypes";
import type { PlanningMealType } from "./types";

const AUTHORITY_MEAL_TYPES = [
  "breakfast",
  "lunch",
  "snack",
  "dinner",
] as const satisfies readonly PlanningMealType[];

export type NutritionPlanAuthorityMeal = {
  meal_type: PlanningMealType;
  state: NutritionPlanAuthorityState;
};

export type NutritionPlanAuthorityOverview = {
  effective_date: string;
  state: NutritionPlanAuthorityState;
  active_plans: NutritionPlanSummary[];
  meals: NutritionPlanAuthorityMeal[];
};

async function errorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    // Fall through to status text.
  }
  return response.statusText || `HTTP ${response.status}`;
}

async function getEffectiveNutritionPlan(
  personId: string,
  effectiveDate: string,
  mealType: PlanningMealType,
): Promise<EffectiveNutritionPlan> {
  const query = new URLSearchParams({
    on_date: effectiveDate,
    meal_type: mealType,
  });
  const response = await fetch(
    buildApiUrl(
      `/api/persons/${encodeURIComponent(personId)}/effective-nutrition-plan?${query.toString()}`,
    ),
    { headers: { Accept: "application/json" } },
  );
  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }
  return (await response.json()) as EffectiveNutritionPlan;
}

export function summarizeNutritionPlanAuthority(
  plans: EffectiveNutritionPlan[],
): NutritionPlanAuthorityOverview {
  const firstPlan = plans[0];
  if (!firstPlan) {
    throw new Error("At least one effective NutritionPlan response is required.");
  }

  const states = plans.map((plan) => plan.nutrition_plan_authority.state);
  let state: NutritionPlanAuthorityState;
  if (states.includes("plan_conflict")) {
    state = "plan_conflict";
  } else if (states.every((item) => item === "no_active_plan")) {
    state = "no_active_plan";
  } else if (states.every((item) => item === "active_plan")) {
    state = "active_plan";
  } else {
    state = "partial_plan_coverage";
  }

  const activePlans = new Map<string, NutritionPlanSummary>();
  for (const plan of plans) {
    for (const activePlan of plan.nutrition_plan_authority.active_plans) {
      activePlans.set(activePlan.id, activePlan);
    }
  }

  return {
    effective_date: firstPlan.effective_date,
    state,
    active_plans: [...activePlans.values()].sort((left, right) =>
      left.title.localeCompare(right.title),
    ),
    meals: plans.map((plan) => ({
      meal_type: plan.meal_type,
      state: plan.nutrition_plan_authority.state,
    })),
  };
}

export async function getNutritionPlanAuthorityOverview(
  personId: string,
  effectiveDate: string,
): Promise<NutritionPlanAuthorityOverview> {
  const plans = await Promise.all(
    AUTHORITY_MEAL_TYPES.map((mealType) =>
      getEffectiveNutritionPlan(personId, effectiveDate, mealType),
    ),
  );
  return summarizeNutritionPlanAuthority(plans);
}
