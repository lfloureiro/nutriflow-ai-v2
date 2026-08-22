import { describe, expect, it } from "vitest";

import type { FamilyDashboard } from "./api/types";
import { mealParticipantNames } from "./MealsScreen";

const dashboard: FamilyDashboard = {
  family_id: "family-1",
  family_name: "Demo",
  timezone: "Europe/Lisbon",
  dashboard_date: "2026-08-22",
  members: [
    {
      person_id: "person-1",
      first_name: "Marta",
      last_name: "Demo",
      timezone: "Europe/Lisbon",
      health: null,
      nutrition: null,
    },
    {
      person_id: "person-2",
      first_name: "Rui",
      last_name: "Demo",
      timezone: "Europe/Lisbon",
      health: null,
      nutrition: null,
    },
  ],
  meals: [],
};

describe("mealParticipantNames", () => {
  it("returns known participant names in the requested order", () => {
    expect(mealParticipantNames(dashboard, ["person-2", "person-1"])).toBe(
      "Rui Demo · Marta Demo",
    );
  });

  it("ignores participant ids that are not in the dashboard member list", () => {
    expect(mealParticipantNames(dashboard, ["missing", "person-1"])).toBe("Marta Demo");
  });
});
