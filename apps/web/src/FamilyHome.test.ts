import { describe, expect, it } from "vitest";

import type { FamilyDashboardMember } from "./api/types";
import { formatMealTime, memberDisplayName } from "./FamilyHome";

const member: FamilyDashboardMember = {
  person_id: "person-1",
  first_name: "Ana",
  last_name: "Silva",
  timezone: "Europe/Lisbon",
  health: null,
  nutrition: null,
};

describe("Family Home presentation helpers", () => {
  it("builds the human member name without exposing identifiers", () => {
    expect(memberDisplayName(member)).toBe("Ana Silva");
  });

  it("formats meal time in the Family timezone", () => {
    expect(formatMealTime("2026-08-22T19:00:00Z", "Europe/Lisbon", "pt-PT")).toBe(
      "20:00",
    );
  });

  it("does not apply the browser timezone when another timezone is requested", () => {
    expect(formatMealTime("2026-08-22T19:00:00Z", "UTC", "pt-PT")).toBe("19:00");
  });
});
