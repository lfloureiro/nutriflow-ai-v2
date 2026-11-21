import { describe, expect, it } from "vitest";
import type { FamilyMealPlan, MealPlanEntry } from "./api/mealPlanTypes";
import { familyLocalDate, familyMealInstant, nextMealSlot } from "./nextMealSelection";

const plan = (days: FamilyMealPlan["days"]): FamilyMealPlan => ({
  family_id: "family", family_name: "Família", timezone: "Europe/Lisbon",
  start_date: days[0]?.date ?? "2026-11-20", end_date: days.at(-1)?.date ?? "2026-11-21", days,
});
const planned = (scheduled_at: string, status = "planned"): MealPlanEntry => ({
  id: "meal", meal_type: "dinner", title: "Jantar planeado", scheduled_at,
  local_time: "20:00", status, recipe_id: null, recipe_name: null,
  location: null, notes: null, transformations: [], participants: [],
});
const days = [
  { date: "2026-11-20", slots: [
    { meal_type: "breakfast" as const, meals: [] },
    { meal_type: "lunch" as const, meals: [] },
    { meal_type: "snack" as const, meals: [] },
    { meal_type: "dinner" as const, meals: [planned("2026-11-20T20:00:00Z")] },
  ] },
  { date: "2026-11-21", slots: [
    { meal_type: "breakfast" as const, meals: [] },
    { meal_type: "lunch" as const, meals: [] },
    { meal_type: "snack" as const, meals: [] },
    { meal_type: "dinner" as const, meals: [] },
  ] },
];

describe("next household meal", () => {
  it("uses family-local calendar dates and summer/winter offsets", () => {
    expect(familyLocalDate(Date.parse("2026-11-20T23:30:00Z"), "Europe/Lisbon")).toBe("2026-11-20");
    expect(familyMealInstant("2026-11-20", "lunch", "Europe/Lisbon")).toBe("2026-11-20T13:00:00.000Z");
    expect(familyMealInstant("2026-07-20", "lunch", "Europe/Lisbon")).toBe("2026-07-20T12:00:00.000Z");
  });
  it("selects the next empty slot rather than a later saved dinner", () => {
    const result = nextMealSlot(plan(days), Date.parse("2026-11-20T10:00:00Z"));
    expect(result?.mealType).toBe("lunch");
    expect(result?.entry).toBeNull();
  });
  it("shows a real saved dinner when it is next", () => {
    const result = nextMealSlot(plan(days), Date.parse("2026-11-20T18:00:00Z"));
    expect(result?.entry?.title).toBe("Jantar planeado");
  });
  it("advances to tomorrow after dinner, never resurrecting a past meal", () => {
    const result = nextMealSlot(plan(days), Date.parse("2026-11-20T21:00:00Z"));
    expect(result?.date).toBe("2026-11-21");
    expect(result?.mealType).toBe("breakfast");
  });
  it("skips an already completed slot", () => {
    const completed = structuredClone(days);
    completed[0]!.slots[3]!.meals[0]!.status = "completed";
    const result = nextMealSlot(plan(completed), Date.parse("2026-11-20T19:00:00Z"));
    expect(result?.date).toBe("2026-11-21");
  });
  it("supports half-hour timezone offsets", () => {
    expect(familyMealInstant("2026-11-20", "breakfast", "Asia/Kolkata")).toBe("2026-11-20T03:00:00.000Z");
  });
});
