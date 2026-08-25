import { describe, expect, it } from "vitest";

import type { PlanningCandidate, PlanningMealType } from "./api/types";
import {
  RECOMMENDATION_SOURCES,
  recommendationCandidates,
  recommendationDates,
  recommendationDeliveryProviderKeys,
  recommendationSourceKinds,
} from "./recommendationPlanning";

function candidate(
  kind: "food_item" | "recipe",
  category: string,
  id: string,
  suitableMealTypes: PlanningMealType[] = ["lunch", "dinner"],
): PlanningCandidate {
  return {
    candidate_kind: kind,
    composition_id: id,
    catalog_key: `${kind}:${id}`,
    name: id,
    category,
    brand: null,
    description: null,
    reference_quantity: "100",
    reference_unit: "g",
    energy_kcal: "200",
    composition_version: "v1",
    composition_at: "2026-08-22T12:00:00Z",
    suitable_meal_types: suitableMealTypes,
  };
}

describe("recommendation planning helpers", () => {
  it("exposes recipes, delivery providers and restaurant discovery", () => {
    expect(RECOMMENDATION_SOURCES).toEqual([
      "cooked",
      "uber_eats",
      "glovo",
      "bolt_food",
      "restaurant",
    ]);
  });

  it("returns one day in single-day mode", () => {
    expect(recommendationDates("single", "2026-08-22", "2026-08-30")).toEqual([
      "2026-08-22",
    ]);
  });

  it("expands an inclusive multi-day range", () => {
    expect(recommendationDates("range", "2026-08-22", "2026-08-24")).toEqual([
      "2026-08-22",
      "2026-08-23",
      "2026-08-24",
    ]);
  });

  it("sends restaurant menu and delivery sources into practical ranking", () => {
    expect(
      recommendationSourceKinds([
        "cooked",
        "uber_eats",
        "glovo",
        "bolt_food",
        "restaurant",
      ]),
    ).toEqual(["home", "restaurant", "delivery"]);
    expect(
      recommendationDeliveryProviderKeys(["uber_eats", "glovo", "bolt_food"]),
    ).toEqual(["uber_eats", "glovo", "bolt_food"]);
  });

  it("allows menu-backed restaurant dishes into nutritional ranking", () => {
    const candidates = [
      candidate("recipe", "recipe", "recipe-1"),
      candidate("food_item", "dish", "dish-1"),
      candidate("food_item", "ingredient", "ingredient-1"),
    ];

    expect(
      recommendationCandidates(candidates, ["cooked", "restaurant"], "lunch").map(
        (item) => item.composition_id,
      ),
    ).toEqual(["recipe-1", "dish-1"]);
    expect(
      recommendationCandidates(candidates, ["bolt_food"], "lunch").map(
        (item) => item.composition_id,
      ),
    ).toEqual(["dish-1"]);
  });

  it("keeps breakfast, snack and main-meal candidates in their own slots", () => {
    const candidates = [
      candidate("recipe", "recipe", "breakfast", ["breakfast"]),
      candidate("recipe", "recipe", "snack", ["snack"]),
      candidate("recipe", "recipe", "main", ["lunch", "dinner"]),
      candidate("food_item", "dish", "commercial-main", ["lunch", "dinner"]),
    ];

    expect(
      recommendationCandidates(candidates, ["cooked"], "breakfast").map(
        (item) => item.composition_id,
      ),
    ).toEqual(["breakfast"]);
    expect(
      recommendationCandidates(candidates, ["cooked"], "snack").map(
        (item) => item.composition_id,
      ),
    ).toEqual(["snack"]);
    expect(
      recommendationCandidates(candidates, ["cooked", "restaurant"], "lunch").map(
        (item) => item.composition_id,
      ),
    ).toEqual(["main", "commercial-main"]);
    expect(
      recommendationCandidates(candidates, ["cooked", "bolt_food"], "dinner").map(
        (item) => item.composition_id,
      ),
    ).toEqual(["main", "commercial-main"]);
  });
});
