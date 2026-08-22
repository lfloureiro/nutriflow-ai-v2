import { describe, expect, it } from "vitest";

import type { PlanningCandidate } from "./api/types";
import {
  candidateDraftFromBootstrap,
  candidatePayload,
  hasCandidateValue,
  localDateTimeValue,
  localDateValue,
  type CandidateDraft,
} from "./planning";

describe("planning form helpers", () => {
  it("formats local date and date-time values for HTML controls", () => {
    const value = new Date(2026, 7, 22, 9, 5);
    expect(localDateValue(value)).toBe("2026-08-22");
    expect(localDateTimeValue(value)).toBe("2026-08-22T09:05");
  });

  it("trims candidate payload fields without changing the candidate kind", () => {
    const draft: CandidateDraft = {
      rowId: "row-1",
      candidate_kind: "recipe",
      composition_id: "  composition-id  ",
      quantity: " 250 ",
      quantity_unit: " g ",
    };

    const payload = candidatePayload(draft);
    expect(payload).toEqual({
      candidate_kind: "recipe",
      composition_id: "composition-id",
      quantity: "250",
      quantity_unit: "g",
    });
    expect(hasCandidateValue(payload)).toBe(true);
  });

  it("uses the server-selected composition and reference serving for a bootstrap candidate", () => {
    const candidate: PlanningCandidate = {
      candidate_kind: "food_item",
      composition_id: "composition-1",
      catalog_key: "food:banana",
      name: "Banana",
      category: "generic",
      brand: null,
      description: null,
      reference_quantity: "100.0000",
      reference_unit: "g",
      energy_kcal: "89.0000",
      composition_version: "v1",
      composition_at: "2026-08-20T10:00:00Z",
    };

    expect(candidateDraftFromBootstrap(candidate, "row-2")).toEqual({
      rowId: "row-2",
      candidate_kind: "food_item",
      composition_id: "composition-1",
      quantity: "100.0000",
      quantity_unit: "g",
    });
  });
});
