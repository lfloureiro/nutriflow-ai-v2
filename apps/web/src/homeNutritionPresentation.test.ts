import {describe,expect,it} from "vitest";
import type {FamilyDashboardMember} from "./api/types";
import {displayedNutrition,isPastDashboardDate,plannedMealProgress,scheduledMemberNutrition} from "./homeNutritionPresentation";
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
  it("estimates each person's progress from their own elapsed meals without mutating intake",()=>{
    const now=Date.parse("2026-11-21T18:05:00Z");
    const meals=[
      {scheduled_at:"2026-11-21T09:00:00Z",status:"planned",participant_person_ids:["p1"]},
      {scheduled_at:"2026-11-21T13:00:00Z",status:"planned",participant_person_ids:["p2"]},
      {scheduled_at:"2026-11-21T20:00:00Z",status:"planned",participant_person_ids:["p1"]},
      {scheduled_at:"2026-11-21T15:00:00Z",status:"cancelled",participant_person_ids:["p1"]},
    ];
    const before=JSON.stringify(member);
    expect(scheduledMemberNutrition(member,"2026-11-21","2026-11-21",meals,now))
      .toEqual({consumed:950,planned:1900,ratio:50,source:"scheduled"});
    expect(JSON.stringify(member)).toBe(before);
    expect(scheduledMemberNutrition({...member,nutrition:null},"2026-11-21","2026-11-21",meals,now))
      .toEqual({consumed:null,planned:null,ratio:50,source:"scheduled"});
    expect(scheduledMemberNutrition(member,"2026-11-22","2026-11-21",meals,now).source).toBe("missing");
  });
  it("confirmed intake always supersedes the inferred schedule",()=>{
    const actual={...member,nutrition:{...member.nutrition!,energy_consumed_kcal:"700"}};
    const meals=[{scheduled_at:"2026-11-21T09:00:00Z",status:"planned",participant_person_ids:["p1"]}];
    expect(scheduledMemberNutrition(actual,"2026-11-21","2026-11-21",meals,Date.now()).source)
      .toBe("recorded");
  });
  it("does not mark an ongoing dinner complete just because 20:00 passed",()=>{
    const now=Date.parse("2026-11-21T20:22:00Z");
    const meals=[
      {id:"lunch",scheduled_at:"2026-11-21T13:00:00Z",status:"planned",participant_person_ids:["p1"]},
      {id:"snack",scheduled_at:"2026-11-21T17:00:00Z",status:"planned",participant_person_ids:["p1"]},
      {id:"dinner",scheduled_at:"2026-11-21T20:00:00Z",status:"planned",participant_person_ids:["p1"]},
    ];
    expect(plannedMealProgress(meals,now,"dinner")).toEqual({elapsed:2,total:3});
    expect(scheduledMemberNutrition(member,"2026-11-21","2026-11-21",meals,now,"dinner"))
      .toEqual({consumed:1267,planned:1900,ratio:67,source:"scheduled"});
    const finished=meals.map(meal=>meal.id==="dinner"?{...meal,status:"completed"}:meal);
    expect(plannedMealProgress(finished,now,"dinner")).toEqual({elapsed:3,total:3});
    expect(scheduledMemberNutrition(member,"2026-11-21","2026-11-21",finished,now,"dinner").ratio).toBe(100);
  });
  it("keeps each participant's count independent",()=>{
    const now=Date.parse("2026-11-21T20:22:00Z");
    const meals=[
      {id:"lunch",scheduled_at:"2026-11-21T13:00:00Z",status:"planned",participant_person_ids:["p1","p2"]},
      {id:"dinner",scheduled_at:"2026-11-21T20:00:00Z",status:"planned",participant_person_ids:["p2"]},
    ];
    expect(scheduledMemberNutrition(member,"2026-11-21","2026-11-21",meals,now,"dinner").ratio).toBe(100);
    expect(scheduledMemberNutrition({...member,person_id:"p2"},"2026-11-21","2026-11-21",meals,now,"dinner").ratio).toBe(50);
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
