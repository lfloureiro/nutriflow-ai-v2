import type {MealType} from "./api/mealPlanTypes";
import type {WeekSetup} from "./api/planningWorkspaceClient";
import {calendarDateOffset} from "./mealAlternatives";

/** Copy organisation only: never copy restrictions, versions or saved meals. */
export function copyWeeklyOrganisation(source: WeekSetup, target: WeekSetup, availableIds: string[]): WeekSetup {
  if (source.person_ids.some(id => !availableIds.includes(id))) throw new Error("unavailable_attendee");
  return {...target, person_ids:[...source.person_ids], meal_types:[...source.meal_types],
    meal_sources:{...source.meal_sources},
    attendance:(source.attendance ?? []).map(entry => {
      const offset=Math.round((Date.parse(entry.planning_date)-Date.parse(source.week_start))/86400000);
      if (offset<0 || offset>6 || !source.meal_types.includes(entry.meal_type) || entry.person_ids.some(id=>!source.person_ids.includes(id))) throw new Error("invalid_source_attendance");
      return {...entry, planning_date:calendarDateOffset(target.week_start,offset),person_ids:[...entry.person_ids]};
    })};
}

/** Expand a group to one meal type; other meals and the week's defaults survive. */
export function repeatMealAttendance(setup:WeekSetup, meal:MealType, personIds:string[]):WeekSetup {
  if(!setup.meal_types.includes(meal) || personIds.some(id=>!setup.person_ids.includes(id)) || new Set(personIds).size!==personIds.length) throw new Error("invalid_attendance");
  return {...setup,attendance:[...(setup.attendance ?? []).filter(entry=>entry.meal_type!==meal),
    ...Array.from({length:7},(_,offset)=>({planning_date:calendarDateOffset(setup.week_start,offset),meal_type:meal,person_ids:[...personIds]}))]};
}
