import { describe, expect, it } from "vitest";

import type { Recipe } from "./api/recipeTypes";
import {
  recipeEvidenceMessage,
  foodCategoryLabel,
  recipeEvidenceSummary,
} from "./RecipeEvidencePanel";

function recipe(overrides: Partial<Recipe> = {}): Recipe {
  return {
    id: "recipe",
    family_id: null,
    scope: "shared",
    editable: false,
    recipe_key: "legacy-v1:recipe:4",
    name: "Mac and Cheese",
    description: null,
    suitable_meal_types: ["lunch", "dinner"],
    yield_quantity: null,
    yield_unit: null,
    serving_count: "6",
    source: "legacy-v1",
    is_active: true,
    ingredients: [
      {
        id: "ingredient-1",
        food_item_id: "food-1",
        food_item_name: "Massa",
        quantity: "450",
        unit: "g",
        preparation: null,
        notes: null,
        sort_order: 0,
        has_nutrition: false,
        has_energy: false,
        classifications: [
          {
            id: "class-1",
            classification_type: "food_category",
            classification_key: "gluten",
            source: "curated",
            source_reference: null,
          },
        ],
      },
      {
        id: "ingredient-2",
        food_item_id: "food-2",
        food_item_name: "Queijo",
        quantity: "350",
        unit: "g",
        preparation: null,
        notes: null,
        sort_order: 1,
        has_nutrition: true,
        has_energy: true,
        classifications: [],
      },
    ],
    latest_composition: {
      id: "composition",
      reference_quantity: "6",
      reference_unit: "serving",
      energy_kcal: "5899",
      energy_per_serving_kcal: "983.17",
      composition_version: "legacy",
      calculation_version: "legacy",
      evidence: "imported",
      computed_at: "2026-09-19T00:00:00Z",
      nutrients: [],
    },
    nutrition_issues: ["missing ingredient composition"],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("Recipe food category labels", () => {
  it("renders canonical food categories for people", () => {
    expect(foodCategoryLabel("gluten", "pt-PT")).toBe("glúten");
    expect(foodCategoryLabel("refined_flour", "pt-PT")).toBe("farinha refinada");
  });
});


describe("Recipe nutrition evidence", () => {
  it("makes an energy-only legacy recipe visibly incomplete", () => {
    const summary = recipeEvidenceSummary(recipe());

    expect(summary).toEqual({
      evidence: "imported",
      ingredientCount: 2,
      nutritionIngredientCount: 1,
      energyIngredientCount: 1,
      nutrientCount: 0,
      hasEnergy: true,
      hasIssues: true,
    });
    expect(recipeEvidenceMessage(summary, "pt-PT")).toContain(
      "macronutrientes",
    );
  });

  it("recognizes complete ingredient-calculated evidence", () => {
    const complete = recipe({
      ingredients: recipe().ingredients.map((ingredient) => ({
        ...ingredient,
        has_nutrition: true,
        has_energy: true,
        classifications: [],
      })),
      nutrition_issues: [],
      latest_composition: {
        ...recipe().latest_composition!,
        evidence: "ingredient_calculated",
        nutrients: [
          {
            key: "protein",
            total_value: "120",
            unit: "g",
            per_serving_value: "20",
          },
        ],
      },
    });
    const summary = recipeEvidenceSummary(complete);

    expect(summary.nutrientCount).toBe(1);
    expect(summary.nutritionIngredientCount).toBe(2);
    expect(recipeEvidenceMessage(summary, "pt-PT")).toContain(
      "permite avaliar",
    );
  });
});
