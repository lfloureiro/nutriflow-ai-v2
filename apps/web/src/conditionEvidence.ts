import type { HealthCondition } from "./api/dietaryReviewClient";

type ConditionEvidenceInput = Pick<HealthCondition,
  "source" | "source_reference" | "started_on" | "ended_on" | "status">;

/** Describe only the recorded evidence; this is not a diagnosis or dietary rule. */
export function conditionEvidenceSummary(row: ConditionEvidenceInput) {
  const hasSourceReference = Boolean(row.source_reference?.trim());
  const hasStartDate = Boolean(row.started_on);
  const hasEndDate = Boolean(row.ended_on);
  return {
    hasSourceReference,
    hasStartDate,
    hasEndDate,
    // Source and status are user-managed metadata, never a proof of certification.
    needsProfessionalEvidence: row.status === "confirmed" &&
      (row.source === "user" || !hasSourceReference),
    hasIncompleteTimeline: !hasStartDate || !hasEndDate,
  };
}
