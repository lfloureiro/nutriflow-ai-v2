import { describe, expect, it } from "vitest";

import { recipesForMealType, startOfWeekDate } from "./FamilyMeals";
import type { Recipe } from "./api/recipeTypes";

describe("family meal-plan helpers", () => {
  it("finds the Monday for a local ISO date", () => {
    expect(startOfWeekDate("2026-08-22")).toBe("2026-08-17");
    expect(startOfWeekDate("2026-08-17")).toBe("2026-08-17");
    expect(startOfWeekDate("2026-08-23")).toBe("2026-08-17");
  });

  it("shows only recipes suitable for the selected meal slot", () => {
    const recipes = [
      { id: "breakfast", suitable_meal_types: ["breakfast"] },
      { id: "main", suitable_meal_types: ["lunch", "dinner"] },
      { id: "snack", suitable_meal_types: ["snack"] },
    ] as unknown as Recipe[];

    expect(recipesForMealType(recipes, "breakfast").map((recipe) => recipe.id)).toEqual([
      "breakfast",
    ]);
    expect(recipesForMealType(recipes, "lunch").map((recipe) => recipe.id)).toEqual([
      "main",
    ]);
    expect(recipesForMealType(recipes, "snack").map((recipe) => recipe.id)).toEqual([
      "snack",
    ]);
  });
});
