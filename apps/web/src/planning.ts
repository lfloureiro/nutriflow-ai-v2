import type {
  PlanningCandidate,
  PracticalSourceKind,
  RecommendationCandidateInput,
} from "./api/types";

export type CandidateDraft = RecommendationCandidateInput & {
  rowId: string;
};

export const DEFAULT_SOURCE_KINDS: PracticalSourceKind[] = [
  "home",
  "pantry",
  "restaurant",
  "delivery",
];

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

export function localDateValue(date = new Date()): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function localDateTimeValue(date = new Date()): string {
  return `${localDateValue(date)}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function scheduledIso(localDateTime: string): string {
  const parsed = new Date(localDateTime);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error("Invalid local date/time value.");
  }
  return parsed.toISOString();
}

export function newCandidateDraft(rowId: string = crypto.randomUUID()): CandidateDraft {
  return {
    rowId,
    candidate_kind: "food_item",
    composition_id: "",
    quantity: "100",
    quantity_unit: "g",
  };
}

export function candidateDraftFromBootstrap(
  candidate: PlanningCandidate,
  rowId: string = crypto.randomUUID(),
): CandidateDraft {
  return {
    rowId,
    candidate_kind: candidate.candidate_kind,
    composition_id: candidate.composition_id,
    quantity: candidate.reference_quantity,
    quantity_unit: candidate.reference_unit,
  };
}

export function candidatePayload(draft: CandidateDraft): RecommendationCandidateInput {
  return {
    candidate_kind: draft.candidate_kind,
    composition_id: draft.composition_id.trim(),
    quantity: draft.quantity.trim(),
    quantity_unit: draft.quantity_unit.trim(),
  };
}

export function hasCandidateValue(candidate: RecommendationCandidateInput): boolean {
  return (
    candidate.composition_id.length > 0 &&
    candidate.quantity.length > 0 &&
    candidate.quantity_unit.length > 0
  );
}
