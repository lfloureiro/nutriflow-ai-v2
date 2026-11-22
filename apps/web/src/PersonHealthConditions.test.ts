import { describe, expect, it } from "vitest";
import { conditionDraftChanged } from "./PersonHealthConditions";
import type { ConditionInput } from "./api/dietaryReviewClient";

const initial: ConditionInput = {
  code: "example",
  name: "Example condition",
  status: "reported",
  source: "user",
  source_reference: null,
  started_on: null,
  ended_on: null,
  notes: null,
};

describe("individual condition edit draft guard", () => {
  it("does not flag an unchanged condition when opening the editor", () => {
    expect(conditionDraftChanged(initial, { ...initial })).toBe(false);
  });
  it("detects edits to evidence, source and dates without changing values", () => {
    expect(conditionDraftChanged(initial, { ...initial, notes: "To review" })).toBe(true);
    expect(conditionDraftChanged(initial, { ...initial, source: "doctor" })).toBe(true);
    expect(conditionDraftChanged(initial, { ...initial, started_on: "2026-11-19" })).toBe(true);
  });
  it("allows discarding an edit by returning to the original snapshot", () => {
    const changed: ConditionInput = { ...initial, name: "Updated" };
    expect(conditionDraftChanged(initial, changed)).toBe(true);
    expect(conditionDraftChanged(initial, { ...changed, name: initial.name })).toBe(false);
  });
});
