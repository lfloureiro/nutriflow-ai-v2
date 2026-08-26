import type {
  PlanningCandidate,
  PracticalSourceKind,
  RecommendationCandidateInput,
} from "./api/types";

export type RecommendationPeriodMode = "single" | "range";
export type RecommendationSource =
  | "cooked"
  | "uber_eats"
  | "glovo"
  | "bolt_food"
  | "restaurant";
export type RecommendationMealType = "breakfast" | "lunch" | "snack" | "dinner";

// Keep the current recommendation surface focused on the two sources that are ready for
// end-to-end use. The remaining source identifiers stay supported internally so they can be
// re-enabled without changing the recommendation request model.
export const RECOMMENDATION_SOURCES = [
  "cooked",
  "uber_eats",
] as const satisfies readonly RecommendationSource[];

export const RECOMMENDATION_MEAL_TYPES: RecommendationMealType[] = [
  "breakfast",
  "lunch",
  "snack",
  "dinner",
];

export const DEFAULT_MEAL_TIMES: Record<RecommendationMealType, string> = {
  breakfast: "08:30",
  lunch: "13:00",
  snack: "17:00",
  dinner: "20:00",
};

function parseIsoDate(value: string): Date {
  const result = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(result.getTime())) {
    throw new Error("Invalid ISO calendar date.");
  }
  return result;
}

export function recommendationDates(
  mode: RecommendationPeriodMode,
  startDate: string,
  endDate: string,
): string[] {
  const start = parseIsoDate(startDate);
  const end = mode === "single" ? start : parseIsoDate(endDate);
  if (end < start) {
    throw new Error("End date must not be before start date.");
  }
  const result: string[] = [];
  const cursor = new Date(start);
  while (cursor <= end) {
    result.push(cursor.toISOString().slice(0, 10));
    if (result.length >= 14) {
      if (cursor < end) {
        throw new Error("Recommendation periods are limited to 14 days.");
      }
      break;
    }
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return result;
}

export function recommendationSourceKinds(
  sources: RecommendationSource[],
): PracticalSourceKind[] {
  const result: PracticalSourceKind[] = [];
  if (sources.includes("cooked")) result.push("home");
  if (
    sources.includes("uber_eats") ||
    sources.includes("glovo") ||
    sources.includes("bolt_food")
  ) {
    result.push("delivery");
  }
  if (sources.includes("restaurant")) result.push("restaurant");
  return result;
}

export function recommendationDeliveryProviderKeys(
  sources: RecommendationSource[],
): string[] {
  const providers: string[] = [];
  if (sources.includes("uber_eats")) providers.push("uber_eats");
  if (sources.includes("glovo")) providers.push("glovo");
  if (sources.includes("bolt_food")) providers.push("bolt_food");
  return providers;
}

function commercialDishMatchesSource(
  candidate: PlanningCandidate,
  sources: RecommendationSource[],
): boolean {
  const key = candidate.catalog_key.toLowerCase();
  if (sources.includes("restaurant") && key.startsWith("external:restaurant_website:")) {
    return true;
  }
  if (sources.includes("uber_eats") && key.startsWith("external:uber_eats:")) {
    return true;
  }
  if (sources.includes("glovo") && key.startsWith("external:glovo:")) {
    return true;
  }
  if (sources.includes("bolt_food") && key.startsWith("external:bolt_food:")) {
    return true;
  }
  return false;
}

function recommendationQuantity(candidate: PlanningCandidate): string {
  const unit = candidate.reference_unit.trim().toLowerCase();
  if (
    candidate.candidate_kind === "recipe" &&
    ["serving", "portion", "dose"].includes(unit)
  ) {
    // Legacy recipes can store total recipe nutrition against an inferred number of servings.
    // Recommendations start from one serving; the backend portion-sizing step can then adjust
    // that serving to the individual's meal budget.
    return "1";
  }
  return candidate.reference_quantity;
}

export function recommendationCandidates(
  candidates: PlanningCandidate[],
  sources: RecommendationSource[],
  mealType: RecommendationMealType,
): RecommendationCandidateInput[] {
  const allowCooked = sources.includes("cooked");
  return candidates
    .filter((candidate) => {
      if (!candidate.suitable_meal_types.includes(mealType)) return false;
      if (candidate.candidate_kind === "recipe") return allowCooked;
      return candidate.category === "dish" && commercialDishMatchesSource(candidate, sources);
    })
    .slice(0, 100)
    .map((candidate) => ({
      candidate_kind: candidate.candidate_kind,
      composition_id: candidate.composition_id,
      quantity: recommendationQuantity(candidate),
      quantity_unit: candidate.reference_unit,
    }));
}

export function recommendationScheduledLocal(
  isoDate: string,
  mealType: RecommendationMealType,
  localTime = DEFAULT_MEAL_TIMES[mealType],
): string {
  return `${isoDate}T${localTime}`;
}
