import type {MealType} from "./api/mealPlanTypes";
import type {AttendanceDecision, WeekSetup} from "./api/planningWorkspaceClient";
import {calendarDateOffset} from "./mealAlternatives";

/** Copy organisation only: never copy restrictions, versions or saved meals. */
export function copyWeeklyOrganisation(source: WeekSetup, target: WeekSetup, availableIds: string[]): WeekSetup {
  if (source.person_ids.some(id => !availableIds.includes(id))) throw new Error("unavailable_attendee");
  return {...target, person_ids:[...source.person_ids], meal_types:[...source.meal_types],
    guest_notices:[], // Guests are one-off exceptions; do not carry them to another week.
    meal_sources:{...source.meal_sources},
    attendance_decisions:(source.attendance_decisions ?? []).map(entry => {
      const offset=Math.round((Date.parse(entry.planning_date)-Date.parse(source.week_start))/86400000);
      if(offset<0||offset>6||!source.meal_types.includes(entry.meal_type)
        ||entry.people.some(person=>!source.person_ids.includes(person.person_id))) {
        throw new Error("invalid_source_attendance_decisions");
      }
      return {...entry,planning_date:calendarDateOffset(target.week_start,offset),
        people:entry.people.map(person=>({...person}))};
    }),
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

/** A recorded attendance decision never silently modifies meal generation or saved meals. */
export function setWeeklyAttendanceDecision(
  setup:WeekSetup,date:string,meal:MealType,personId:string,decision:AttendanceDecision,
):WeekSetup {
  if(!setup.meal_types.includes(meal)||!setup.person_ids.includes(personId)
    ||date<setup.week_start||date>calendarDateOffset(setup.week_start,6)) {
    throw new Error("invalid_attendance_decision");
  }
  const previous=setup.attendance_decisions ?? [];
  const existing=previous.find(row=>row.planning_date===date&&row.meal_type===meal);
  const people=[...(existing?.people ?? []).filter(person=>person.person_id!==personId),
    {person_id:personId,decision}];
  return {...setup,attendance_decisions:[
    ...previous.filter(row=>row.planning_date!==date||row.meal_type!==meal),
    {planning_date:date,meal_type:meal,people},
  ]};
}

/** Guest headcounts are advisory; never add a guest to saved meal participants. */
export function setWeeklyGuestCount(
  setup:WeekSetup,date:string,meal:MealType,count:number,
):WeekSetup {
  if(!setup.meal_types.includes(meal)||date<setup.week_start
    ||date>calendarDateOffset(setup.week_start,6)
    ||!Number.isInteger(count)||count<0||count>12) {
    throw new Error("invalid_guest_headcount");
  }
  return {...setup,guest_notices:[
    ...(setup.guest_notices ?? []).filter(row=>row.planning_date!==date||row.meal_type!==meal),
    ...(count>0?[{planning_date:date,meal_type:meal,guest_count:count}]:[]),
  ]};
}
