import { describe, expect, it } from "vitest";

import type { Recipe } from "./api/recipeTypes";
import { recipeNutritionSummary } from "./RecipeCatalogue";

function recipe(energy: string | null, perServing: string | null): Recipe {
  return {
    id: "recipe-1",
    family_id: "family-1",
    recipe_key: "family:test:recipe:1",
    name: "Bolonhesa",
    description: null,
    yield_quantity: "1000",
    yield_unit: "g",
    serving_count: "4",
    source: "user",
    is_active: true,
    ingredients: [],
    latest_composition: {
      id: "composition-1",
      reference_quantity: "1000",
      reference_unit: "g",
      energy_kcal: energy,
      energy_per_serving_kcal: perServing,
      composition_version: "calculated-1",
      calculation_version: "recipe-nutrition-v1",
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
});
