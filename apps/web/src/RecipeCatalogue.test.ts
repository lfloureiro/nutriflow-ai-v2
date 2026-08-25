import { describe, expect, it } from "vitest";

import type { Recipe, RecipeNutritionEvidence } from "./api/recipeTypes";
import {
  matchesMealTypeFilter,
  recipeNutritionBlockers,
  recipeNutritionEvidenceLabel,
  recipeNutritionSummary,
} from "./RecipeCatalogue";

function recipe(
  energy: string | null,
  perServing: string | null,
  ingredients: Recipe["ingredients"] = [],
  evidence: RecipeNutritionEvidence = "ingredient_calculated",
): Recipe {
  return {
    id: "recipe-1",
    family_id: "family-1",
    scope: "family",
    editable: true,
    recipe_key: "family:test:recipe:1",
    name: "Bolonhesa",
    description: null,
    suitable_meal_types: ["lunch", "dinner"],
    yield_quantity: "1000",
    yield_unit: "g",
    serving_count: "4",
    source: "user",
    is_active: true,
    ingredients,
    latest_composition: {
      id: "composition-1",
      reference_quantity: "1000",
      reference_unit: "g",
      energy_kcal: energy,
      energy_per_serving_kcal: perServing,
      composition_version: "calculated-1",
      calculation_version: "recipe-nutrition-v1",
      evidence,
      computed_at: "2026-08-22T12:00:00Z",
      nutrients: [],
    },
    nutrition_issues: [],
    created_at: "2026-08-22T12:00:00Z",
    updated_at: "2026-08-22T12:00:00Z",
  };
}

describe("recipe catalogue helpers", () => {
  it("shows total and per-serving energy", () => {
    expect(recipeNutritionSummary(recipe("2640", "660"), "pt-PT")).toBe(
      "Receita total: 2640 kcal · Por dose: 660 kcal",
    );
  });

  it("keeps missing nutrition explicit", () => {
    expect(recipeNutritionSummary(recipe(null, null), "pt-PT")).toBe(
      "Ainda sem cálculo nutricional utilizável.",
    );
  });

  it("labels practical and development estimates separately", () => {
    expect(
      recipeNutritionEvidenceLabel(
        recipe("2400", "600", [], "ingredient_estimated"),
        "pt-PT",
      ),
    ).toBe("Estimativa nutricional");
    expect(
      recipeNutritionEvidenceLabel(
        recipe("2400", "600", [], "synthetic_development"),
        "pt-PT",
      ),
    ).toBe("Estimativa de desenvolvimento");
    expect(recipeNutritionEvidenceLabel(recipe("2400", "600"), "pt-PT")).toBe(
      "Calculada pelos ingredientes",
    );
  });

  it("filters recipes by meal type instead of nutrition implementation detail", () => {
    const lunchRecipe = recipe("2400", "600");
    const snackRecipe = {
      ...recipe("250", "250", [], "ingredient_estimated"),
      suitable_meal_types: ["snack"] as Recipe["suitable_meal_types"],
    };

    expect(matchesMealTypeFilter(lunchRecipe, "all")).toBe(true);
    expect(matchesMealTypeFilter(lunchRecipe, "lunch")).toBe(true);
    expect(matchesMealTypeFilter(lunchRecipe, "snack")).toBe(false);
    expect(matchesMealTypeFilter(snackRecipe, "snack")).toBe(true);
  });

  it("identifies ingredients without detailed composition", () => {
    expect(
      recipeNutritionBlockers(
        recipe(null, null, [
          {
            id: "ingredient-1",
            food_item_id: "food-1",
            food_item_name: "Arroz",
            quantity: "200",
            unit: "g",
            preparation: null,
            notes: null,
            sort_order: 0,
            has_nutrition: false,
            has_energy: false,
          },
          {
            id: "ingredient-2",
            food_item_id: "food-2",
            food_item_name: "Molho",
            quantity: "100",
            unit: "g",
            preparation: null,
            notes: null,
            sort_order: 1,
            has_nutrition: true,
            has_energy: false,
          },
          {
            id: "ingredient-3",
            food_item_id: "food-3",
            food_item_name: "Carne",
            quantity: "150",
            unit: "g",
            preparation: null,
            notes: null,
            sort_order: 2,
            has_nutrition: true,
            has_energy: true,
          },
        ]),
      ),
    ).toEqual([
      { ingredient: "Arroz", reason: "missing_composition" },
      { ingredient: "Molho", reason: "missing_energy" },
    ]);
  });
});