import {describe,expect,it} from "vitest";
import type {FamilyDashboardMember} from "./api/types";
import {displayedNutrition,isPastDashboardDate,plannedMealProgress} from "./homeNutritionPresentation";
const member:FamilyDashboardMember={
  person_id:"p1",first_name:"Ana",last_name:null,timezone:"Europe/Lisbon",health:null,
  nutrition:{state_date:"2026-11-16",energy_consumed_kcal:"0",energy_planned_kcal:"1900",
    energy_remaining_min_kcal:null,energy_remaining_max_kcal:null,
    adherence_score:null,confidence_score:null,computed_at:"2026-11-21T11:00:00Z"},
};
describe("historical presentation data provenance",()=>{
  it("only samples earlier dates",()=>{
    expect(isPastDashboardDate("2026-11-16","2026-11-21")).toBe(true);
    expect(isPastDashboardDate("2026-11-21","2026-11-21")).toBe(false);
    expect(isPastDashboardDate("2026-11-22","2026-11-21")).toBe(false);
  });
  it("gives deterministic, visibly simulated examples without changing source records",()=>{
    const original=JSON.stringify(member);
    const first=displayedNutrition(member,"2026-11-16","2026-11-21");
    const again=displayedNutrition(member,"2026-11-16","2026-11-21");
    expect(first).toEqual(again);
    expect(first.source).toBe("simulated");
    expect(first.ratio).toBeGreaterThanOrEqual(62);
    expect(first.ratio).toBeLessThanOrEqual(95);
    expect(JSON.stringify(member)).toEqual(original);
    expect(displayedNutrition(member,"2026-11-21","2026-11-21").source).toBe("missing");
  });
  it("never overwrites actual confirmed intake even for a past date",()=>{
    const real={...member,nutrition:{...member.nutrition!,energy_consumed_kcal:"800"}};
    const row=displayedNutrition(real,"2026-11-16","2026-11-21");
    expect(row.source).toBe("recorded");
    expect(row.consumed).toBe(800);
    expect(row.ratio).toBe(42);
  });
  it("does not simulate without planned energy",()=>{
    expect(displayedNutrition({...member,nutrition:null},"2026-11-16","2026-11-21").source).toBe("missing");
  });
  it("shows elapsed scheduled meal times, not consumption",()=>{
    const current=Date.parse("2026-11-21T18:05:00Z");
    const schedule=plannedMealProgress([
      {scheduled_at:"2026-11-21T13:00:00Z",status:"planned"},
      {scheduled_at:"2026-11-21T17:00:00Z",status:"planned"},
      {scheduled_at:"2026-11-21T20:00:00Z",status:"planned"},
      {scheduled_at:"2026-11-21T19:00:00Z",status:"cancelled"},
    ],current);
    expect(schedule).toEqual({elapsed:2,total:3});
  });
});
