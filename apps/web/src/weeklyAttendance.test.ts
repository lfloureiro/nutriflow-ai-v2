import {describe,expect,it} from "vitest";
import {copyWeeklyOrganisation,repeatMealAttendance} from "./weeklyAttendance";
import {mealPlanErrorText} from "./FamilyMeals";
import {ApiError} from "./api/client";
import type {WeekSetup} from "./api/planningWorkspaceClient";
const source:WeekSetup={week_start:"2026-10-19",version:8,person_ids:["a","b","c"],meal_types:["lunch","dinner"],excluded_food_item_ids:["old-exclusion"],meal_sources:{lunch:"delivery",dinner:"home"},attendance:[{planning_date:"2026-10-20",meal_type:"dinner",person_ids:["a","b"]},{planning_date:"2026-10-25",meal_type:"lunch",person_ids:[]}]};
const target:WeekSetup={week_start:"2026-10-26",version:3,person_ids:["a","b"],meal_types:["dinner"],excluded_food_item_ids:["current-exclusion"]};
describe("reusable attendance",()=>{
 it("maps weekdays across DST without copying restrictions or target concurrency version",()=>{
   const result=copyWeeklyOrganisation(source,target,["a","b","c"]);
   expect(result.version).toBe(3);expect(result.week_start).toBe("2026-10-26");
   expect(result.excluded_food_item_ids).toEqual(["current-exclusion"]);
   expect(result.attendance?.map(a=>a.planning_date)).toEqual(["2026-10-27","2026-11-01"]);
   expect(result.attendance?.[1]?.person_ids).toEqual([]);expect(result.meal_sources).toEqual(source.meal_sources);
   expect(source.attendance?.[0]?.planning_date).toBe("2026-10-20");
 });
 it("blocks unavailable attendees and invalid source slots rather than dropping people silently",()=>{
   expect(()=>copyWeeklyOrganisation(source,target,["a","b"])).toThrow("unavailable_attendee");
   expect(()=>copyWeeklyOrganisation({...source,attendance:[{planning_date:"2026-11-01",meal_type:"dinner",person_ids:[]}]},target,source.person_ids)).toThrow("invalid_source_attendance");
 });
 it("repeats a group for one meal and preserves other meals, empty attendance and defaults",()=>{
   const result=repeatMealAttendance(source,"dinner",["b","c"]);
   expect(result.attendance?.filter(a=>a.meal_type==="dinner")).toHaveLength(7);
   expect(result.attendance?.filter(a=>a.meal_type==="dinner").every(a=>a.person_ids.join() === "b,c")).toBe(true);
   expect(result.attendance?.find(a=>a.meal_type==="lunch")?.person_ids).toEqual([]);
   expect(result.person_ids).toEqual(source.person_ids);
   expect(repeatMealAttendance(source,"dinner",[]).attendance?.filter(a=>a.meal_type==="dinner").every(a=>!a.person_ids.length)).toBe(true);
   expect(()=>repeatMealAttendance(source,"dinner",["unknown"])).toThrow();
 });
});

it("explains attendee conflicts with ingredient names and a concrete next step",()=>{
 const error=new ApiError("Recipe conflicts with active attendee restrictions: Cebola. Choose and validate a compatible variant before saving.",422);
 expect(mealPlanErrorText(error,"pt-PT")).toContain("restrições dos presentes: Cebola");
 expect(mealPlanErrorText(error,"pt-PT")).toContain("valida uma variante");
 expect(mealPlanErrorText(error,"en")).toContain("HTTP 422");
});
