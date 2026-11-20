import type { FamilyMealPlan, MealPlanEntry, MealType } from "./api/mealPlanTypes";
import { DEFAULT_MEAL_TIMES } from "./recommendationPlanning";

export const MEAL_ORDER: MealType[] = ["breakfast", "lunch", "snack", "dinner"];

export type NextMealSlot = {
  date: string;
  mealType: MealType;
  scheduledAt: string;
  at: number;
  entry: MealPlanEntry | null;
};

/** Date in the household's timezone, independent of the browser's timezone. */
export function familyLocalDate(now: number, timeZone: string): string {
  const values = new Intl.DateTimeFormat("en-GB", {
    timeZone, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date(now));
  const value = (type: string) => values.find(part => part.type === type)?.value ?? "";
  return `${value("year")}-${value("month")}-${value("day")}`;
}

/** Schedule a household-local mealtime using the timezone offset at local noon.
 * Meal times are after the usual DST transition window; no browser-local parsing.
 */
export function familyMealInstant(date: string, mealType: MealType, timezone: string): string {
  const time = DEFAULT_MEAL_TIMES[mealType];
  const noonUtc = new Date(`${date}T12:00:00Z`);
  if (Number.isNaN(noonUtc.valueOf()) || noonUtc.toISOString().slice(0, 10) !== date) {
    throw new Error("Invalid meal date");
  }
  const zone = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone, timeZoneName: "shortOffset", hour: "2-digit",
  }).formatToParts(noonUtc).find(part => part.type === "timeZoneName")?.value;
  const offset = /^(?:GMT|UTC)(?:([+-])(\d{1,2})(?::(\d{2}))?)?$/.exec(zone ?? "");
  if (!offset) throw new Error("Unsupported timezone");
  const sign = offset[1] === "-" ? -1 : 1;
  const offsetMinutes = sign * (Number(offset[2] ?? "0") * 60 + Number(offset[3] ?? "0"));
  const [hours = 0, minutes = 0] = time.split(":").map(Number);
  const localMinutes = hours * 60 + minutes;
  return new Date(Date.parse(`${date}T12:00:00Z`) + (localMinutes - 720 - offsetMinutes) * 60_000).toISOString();
}

/** Never surface a past slot as the next meal. Completed/cancelled events are not open. */
export function nextMealSlot(plan: FamilyMealPlan, now: number): NextMealSlot | null {
  const upcoming: NextMealSlot[] = [];
  for (const day of plan.days) {
    for (const mealType of MEAL_ORDER) {
      const slot = day.slots.find(item => item.meal_type === mealType);
      const entry = slot?.meals
        .filter(item => !["cancelled", "completed", "served"].includes(item.status))
        .sort((a, b) => Date.parse(a.scheduled_at) - Date.parse(b.scheduled_at))[0] ?? null;
      // A completed slot is already done, even if its default time has not elapsed.
      if (!entry && slot?.meals.some(item => item.status === "completed" || item.status === "served")) continue;
      const scheduledAt = entry?.scheduled_at ?? familyMealInstant(day.date, mealType, plan.timezone);
      const at = Date.parse(scheduledAt);
      if (Number.isFinite(at) && at >= now) upcoming.push({ date: day.date, mealType, scheduledAt, at, entry });
    }
  }
  return upcoming.sort((a, b) => a.at - b.at)[0] ?? null;
}
