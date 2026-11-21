import type {FamilyDashboardMember} from "./api/types";

/** Presentation-only sample for historical dates. This must NEVER enter persisted
 * nutrition/consumption records or be described as measured intake. */
export type PresentedNutrition = {
  consumed: number | null;
  planned: number | null;
  ratio: number | null;
  source: "recorded" | "simulated" | "missing";
};
export function isPastDashboardDate(date: string, today: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(date) && date < today;
}
function fraction(key: string): number {
  let hash=2166136261;
  for (const char of key) hash=Math.imul(hash^char.charCodeAt(0),16777619)>>>0;
  return (hash%1000)/1000;
}
function parseEnergy(value: string | null | undefined): number | null {
  if(value==null||value.trim()==="")return null;
  const parsed=Number(value);
  return Number.isFinite(parsed)&&parsed>=0 ? parsed : null;
}
export function displayedNutrition(member: FamilyDashboardMember, date: string, today: string): PresentedNutrition {
  const actual=parseEnergy(member.nutrition?.energy_consumed_kcal);
  const planned=parseEnergy(member.nutrition?.energy_planned_kcal);
  if(actual!==null&&actual>0){
    return {consumed:actual,planned,source:"recorded",
      ratio:planned!==null&&planned>0?Math.min(100,Math.round(actual/planned*100)):null};
  }
  if(isPastDashboardDate(date,today)&&planned!==null&&planned>0){
    const percent=0.62+fraction(date+"|"+member.person_id)*0.33;
    const consumed=Math.round(planned*percent);
    return {consumed,planned,ratio:Math.round(100*consumed/planned),source:"simulated"};
  }
  return {consumed:null,planned,ratio:null,source:"missing"};
}
export function plannedMealProgress(scheduled: Array<{scheduled_at:string;status:string}>,now:number): {elapsed:number;total:number} {
  const valid=scheduled.filter(m=>m.status!=="cancelled"&&Number.isFinite(Date.parse(m.scheduled_at)));
  return {total:valid.length,elapsed:valid.filter(m=>Date.parse(m.scheduled_at)<=now).length};
}
