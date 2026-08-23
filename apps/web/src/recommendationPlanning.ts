import type {
  PlanningCandidate,
  PracticalSourceKind,
  RecommendationCandidateInput,
} from "./api/types";

export type RecommendationPeriodMode = "single" | "range";
export type RecommendationSource = "cooked" | "uber_eats" | "glovo" | "restaurant";
export type RecommendationMealType = "breakfast" | "lunch" | "snack" | "dinner";

export const RECOMMENDATION_SOURCES: RecommendationSource[] = [
  "cooked",
  "uber_eats",
  "glovo",
  "restaurant",
];

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
  if (sources.includes("uber_eats") || sources.includes("glovo")) result.push("delivery");
  if (sources.includes("restaurant")) result.push("restaurant");
  return result;
}

export function recommendationDeliveryProviderKeys(
  sources: RecommendationSource[],
): string[] {
  const providers: string[] = [];
  if (sources.includes("uber_eats")) providers.push("uber_eats");
  if (sources.includes("glovo")) providers.push("glovo");
  return providers;
}

export function recommendationCandidates(
  candidates: PlanningCandidate[],
  sources: RecommendationSource[],
): RecommendationCandidateInput[] {
  const allowCooked = sources.includes("cooked");
  const allowCommercial =
    sources.includes("uber_eats") ||
    sources.includes("glovo") ||
    sources.includes("restaurant");
  return candidates
    .filter((candidate) => {
      if (candidate.candidate_kind === "recipe") return allowCooked;
      return allowCommercial && candidate.category === "dish";
    })
    .slice(0, 100)
    .map((candidate) => ({
      candidate_kind: candidate.candidate_kind,
      composition_id: candidate.composition_id,
      quantity: candidate.reference_quantity,
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
