import { describe, expect, it } from "vitest";

import type { FamilyDashboard } from "./api/types";
import { personMeals } from "./PersonOverview";

const dashboard: FamilyDashboard = {
  family_id: "family-1",
  family_name: "Demo",
  timezone: "Europe/Lisbon",
  dashboard_date: "2026-08-22",
  members: [],
  meals: [
    {
      id: "meal-1",
      meal_type: "lunch",
      title: "Lunch",
      scheduled_at: "2026-08-22T12:00:00Z",
      timezone: "Europe/Lisbon",
      status: "planned",
      location: null,
      participant_person_ids: ["person-1", "person-2"],
    },
    {
      id: "meal-2",
      meal_type: "dinner",
      title: "Dinner",
      scheduled_at: "2026-08-22T19:00:00Z",
      timezone: "Europe/Lisbon",
      status: "planned",
      location: null,
      participant_person_ids: ["person-2"],
    },
  ],
};

describe("person overview helpers", () => {
  it("returns only meals for the selected person", () => {
    expect(personMeals(dashboard, "person-1").map((meal) => meal.id)).toEqual(["meal-1"]);
    expect(personMeals(dashboard, "person-2").map((meal) => meal.id)).toEqual([
      "meal-1",
      "meal-2",
    ]);
  });

  it("returns an empty list when the person has no current-day meals", () => {
    expect(personMeals(dashboard, "person-3")).toEqual([]);
  });
});
