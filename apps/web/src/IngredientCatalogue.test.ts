import { describe, expect, it } from "vitest";

import type { Ingredient } from "./api/ingredientTypes";
import {
  buildIngredientComposition,
  ingredientNutritionSummary,
} from "./IngredientCatalogue";

const baseValues = {
  name: "Aveia",
  brand: "",
  description: "",
  referenceQuantity: "100",
  referenceUnit: "g",
  energy: "",
  protein: "",
  carbohydrate: "",
  fat: "",
  fiber: "",
  sodium: "",
};

function ingredient(composition: Ingredient["latest_composition"]): Ingredient {
  return {
    id: "11111111-1111-4111-8111-111111111111",
    family_id: "22222222-2222-4222-8222-222222222222",
    scope: "family",
    editable: true,
    catalog_key: "family:test:ingredient:test",
    name: "Aveia",
    brand: null,
    description: null,
    source: "user",
    is_active: true,
    latest_composition: composition,
    created_at: "2026-08-22T10:00:00Z",
    updated_at: "2026-08-22T10:00:00Z",
  };
}

describe("ingredient catalogue helpers", () => {
  it("does not create a composition when nutrition is empty", () => {
    expect(buildIngredientComposition(baseValues)).toBeNull();
  });

  it("normalizes decimal commas and emits only populated nutrients", () => {
    expect(
      buildIngredientComposition({
        ...baseValues,
        energy: "370,5",
        protein: "13,2",
        sodium: "4",
      }),
    ).toEqual({
      reference_quantity: "100",
      reference_unit: "g",
      energy_kcal: "370.5",
      nutrients: [
        { key: "protein", value: "13.2", unit: "g" },
        { key: "sodium", value: "4", unit: "mg" },
      ],
    });
  });

  it("shows an explicit missing-composition label", () => {
    expect(ingredientNutritionSummary(ingredient(null), "pt-PT")).toBe(
      "Sem composição nutricional",
    );
  });

  it("formats the latest energy evidence against its reference quantity", () => {
    expect(
      ingredientNutritionSummary(
        ingredient({
          id: "33333333-3333-4333-8333-333333333333",
          reference_quantity: "100.0000",
          reference_unit: "g",
          energy_kcal: "370.0000",
          data_version: "manual-test",
          source: "user",
          source_reference: null,
          effective_at: "2026-08-22T10:00:00Z",
          notes: null,
          nutrients: [],
        }),
        "pt-PT",
      ),
    ).toBe("100 g · 370 kcal");
  });
});
