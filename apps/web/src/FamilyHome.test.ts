import { describe, expect, it } from "vitest";

import type { FamilyDashboardMember } from "./api/types";
import { familyNutritionSummary, formatMealTime, memberDisplayName } from "./FamilyHome";

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

  it("does not interpret zero consumption as progress or clinical adherence", () => {
    const rows = familyNutritionSummary([
      {...member, nutrition:{
        state_date:"2026-11-21",energy_consumed_kcal:"0.00",energy_planned_kcal:"1900",
        energy_remaining_min_kcal:null,energy_remaining_max_kcal:null,
        adherence_score:null,confidence_score:null,computed_at:"2026-11-21T12:00:00Z",
      }},
      {...member,person_id:"person-2",first_name:"Bia",nutrition:{
        state_date:"2026-11-21",energy_consumed_kcal:"720",energy_planned_kcal:"1800",
        energy_remaining_min_kcal:null,energy_remaining_max_kcal:null,
        adherence_score:null,confidence_score:null,computed_at:"2026-11-21T12:00:00Z",
      }},
    ]);
    expect(rows[0]!.hasConfirmedConsumption).toBe(false);
    expect(rows[0]!.ratio).toBe(null);
    expect(rows[1]!.ratio).toBe(40);
    expect(rows[1]!.planned).toBe(1800);
  });

  it("does not fabricate a percentage without positive planned energy", () => {
    const rows = familyNutritionSummary([
      {...member, nutrition:{
        state_date:"2026-11-21",energy_consumed_kcal:"350",energy_planned_kcal:"0",
        energy_remaining_min_kcal:null,energy_remaining_max_kcal:null,
        adherence_score:null,confidence_score:null,computed_at:"2026-11-21T12:00:00Z",
      }},
    ]);
    expect(rows[0]!.ratio).toBe(null);
    expect(rows[0]!.hasConfirmedConsumption).toBe(true);
  });

  it("does not apply the browser timezone when another timezone is requested", () => {
    expect(formatMealTime("2026-08-22T19:00:00Z", "UTC", "pt-PT")).toBe("19:00");
  });
});
