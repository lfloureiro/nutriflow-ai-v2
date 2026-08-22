import { describe, expect, it } from "vitest";

import { startOfWeekDate } from "./FamilyMeals";

describe("family meal-plan helpers", () => {
  it("finds the Monday for a local ISO date", () => {
    expect(startOfWeekDate("2026-08-22")).toBe("2026-08-17");
    expect(startOfWeekDate("2026-08-17")).toBe("2026-08-17");
    expect(startOfWeekDate("2026-08-23")).toBe("2026-08-17");
  });
});
