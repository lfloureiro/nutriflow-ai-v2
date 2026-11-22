import { describe, expect, it } from "vitest";

import { addPlanDays, copyAttendanceSelection, recipesForMealType, startOfWeekDate, type ParticipantDraft } from "./FamilyMeals";
import type { Recipe } from "./api/recipeTypes";

function recipe(id: string, suitableMealTypes: Recipe["suitable_meal_types"]): Recipe {
  return {
    id,
    family_id: null,
    scope: "shared",
    editable: false,
    recipe_key: id,
    name: id,
    description: null,
    suitable_meal_types: suitableMealTypes,
    yield_quantity: null,
    yield_unit: null,
    serving_count: null,
    source: "test",
    is_active: true,
    ingredients: [],
    latest_composition: null,
    nutrition_issues: [],
    created_at: "2026-08-24T00:00:00Z",
    updated_at: "2026-08-24T00:00:00Z",
  };
}

describe("family meal-plan helpers", () => {
  it("finds the Monday for a local ISO date", () => {
    expect(startOfWeekDate("2026-08-22")).toBe("2026-08-17");
    expect(startOfWeekDate("2026-08-17")).toBe("2026-08-17");
    expect(startOfWeekDate("2026-08-23")).toBe("2026-08-17");
  });

  it("moves between days and weeks without timezone drift", () => {
    expect(addPlanDays("2026-09-19", 1)).toBe("2026-09-20");
    expect(addPlanDays("2026-09-19", -1)).toBe("2026-09-18");
    expect(addPlanDays("2026-09-14", 7)).toBe("2026-09-21");
    expect(addPlanDays("2026-09-14", -7)).toBe("2026-09-07");
  });

  it("copies only attendance and leaves every recorded quantity and unit unchanged", () => {
    const original:ParticipantDraft[]=[
      {personId:"a",attendance:"present",quantity:"2.500",unit:"emb"},
      {personId:"b",attendance:"absent",quantity:"0.75",unit:"serving"},
      {personId:"c",attendance:"present",quantity:"",unit:"g"},
    ];
    const copied=copyAttendanceSelection(original,["b","c","unknown"]);
    expect(copied).toEqual([
      {personId:"a",attendance:"absent",quantity:"2.500",unit:"emb"},
      {personId:"b",attendance:"present",quantity:"0.75",unit:"serving"},
      {personId:"c",attendance:"present",quantity:"",unit:"g"},
    ]);
    expect(original[0]?.attendance).toBe("present");
    expect(original[1]?.attendance).toBe("absent");
    expect(copyAttendanceSelection(original,[]).every(person=>person.attendance==="absent")).toBe(true);
  });

  it("never silently treats undecided attendance as confirmed or absent before copying", () => {
    const input:ParticipantDraft[]=[
      {personId:"one",attendance:"unconfirmed" as const,quantity:"",unit:"serving"},
      {personId:"two",attendance:"unconfirmed" as const,quantity:"2",unit:"emb"},
    ];
    expect(input.every(item=>item.attendance==="unconfirmed")).toBe(true);
    expect(copyAttendanceSelection(input,["one"])).toEqual([
      {personId:"one",attendance:"present",quantity:"",unit:"serving"},
      {personId:"two",attendance:"absent",quantity:"2",unit:"emb"},
    ]);
    expect(input[0]?.attendance).toBe("unconfirmed");
    expect(input[1]?.attendance).toBe("unconfirmed");
  });

  it("shows only recipes suitable for the selected meal slot", () => {
    const recipes: Recipe[] = [
      recipe("breakfast", ["breakfast"]),
      recipe("main", ["lunch", "dinner"]),
      recipe("snack", ["snack"]),
    ];

    expect(recipesForMealType(recipes, "breakfast").map((item) => item.id)).toEqual([
      "breakfast",
    ]);
    expect(recipesForMealType(recipes, "lunch").map((item) => item.id)).toEqual(["main"]);
    expect(recipesForMealType(recipes, "snack").map((item) => item.id)).toEqual(["snack"]);
  });
});
