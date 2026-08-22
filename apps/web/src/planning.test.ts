import { describe, expect, it } from "vitest";

import {
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
});
