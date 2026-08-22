import { describe, expect, it } from "vitest";

import type { FamilyMeal } from "./api/types";
import { familyMealParticipantNames, startOfWeekDate } from "./FamilyMeals";

describe("family meals helpers", () => {
  it("finds the Monday for a local ISO date", () => {
    expect(startOfWeekDate("2026-08-22")).toBe("2026-08-17");
    expect(startOfWeekDate("2026-08-17")).toBe("2026-08-17");
    expect(startOfWeekDate("2026-08-23")).toBe("2026-08-17");
  });

  it("formats participant names without exposing ids", () => {
    const meal: FamilyMeal = {
      id: "meal-1",
      meal_type: "dinner",
      title: "Dinner",
      scheduled_at: "2026-08-22T19:00:00Z",
      timezone: "Europe/Lisbon",
      status: "planned",
      location: null,
      participants: [
        {
          person_id: "person-1",
          first_name: "Ana",
          last_name: "Silva",
          status: "planned",
        },
        {
          person_id: "person-2",
          first_name: "Rui",
          last_name: null,
          status: "planned",
        },
      ],
    };

    expect(familyMealParticipantNames(meal)).toBe("Ana Silva · Rui");
  });
});
