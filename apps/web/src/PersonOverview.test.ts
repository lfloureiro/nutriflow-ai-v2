import { describe, expect, it } from "vitest";

import type { FamilyDashboard } from "./api/types";
import { mealStatusLabel, mealTypeLabel, personMeals } from "./PersonOverview";

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

  it("localizes known meal types without inventing unknown values", () => {
    expect(mealTypeLabel("lunch", "pt-PT")).toBe("Almoço");
    expect(mealTypeLabel("dinner", "en")).toBe("Dinner");
    expect(mealTypeLabel("custom", "pt-PT")).toBe("custom");
  });

  it("localizes known meal statuses without inventing unknown values", () => {
    expect(mealStatusLabel("planned", "pt-PT")).toBe("Planeada");
    expect(mealStatusLabel("completed", "pt-PT")).toBe("Concluída");
    expect(mealStatusLabel("custom", "en")).toBe("custom");
  });
});
