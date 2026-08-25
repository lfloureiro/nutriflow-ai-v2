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
  catalogKey = `${kind}:${id}`,
): PlanningCandidate {
  return {
    candidate_kind: kind,
    composition_id: id,
    catalog_key: catalogKey,
    name: id,
    category,
    brand: null,
    description: null,
    reference_quantity: "1",
    reference_unit: kind === "food_item" ? "serving" : "serving",
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

  it("keeps restaurant and delivery dishes on their selected source", () => {
    const candidates = [
      candidate("recipe", "recipe", "recipe-1"),
      candidate(
        "food_item",
        "dish",
        "restaurant-dish",
        ["lunch", "dinner"],
        "external:restaurant_website:abc",
      ),
      candidate(
        "food_item",
        "dish",
        "uber-dish",
        ["lunch", "dinner"],
        "external:uber_eats:def",
      ),
      candidate(
        "food_item",
        "dish",
        "bolt-dish",
        ["lunch", "dinner"],
        "external:bolt_food:ghi",
      ),
    ];

    expect(
      recommendationCandidates(candidates, ["cooked", "restaurant"], "lunch").map(
        (item) => item.composition_id,
      ),
    ).toEqual(["recipe-1", "restaurant-dish"]);
    expect(
      recommendationCandidates(candidates, ["uber_eats"], "lunch").map(
        (item) => item.composition_id,
      ),
    ).toEqual(["uber-dish"]);
    expect(
      recommendationCandidates(candidates, ["bolt_food"], "lunch").map(
        (item) => item.composition_id,
      ),
    ).toEqual(["bolt-dish"]);
  });

  it("keeps breakfast, snack and main-meal candidates in their own slots", () => {
    const candidates = [
      candidate("recipe", "recipe", "breakfast", ["breakfast"]),
      candidate("recipe", "recipe", "snack", ["snack"]),
      candidate("recipe", "recipe", "main", ["lunch", "dinner"]),
      candidate(
        "food_item",
        "dish",
        "restaurant-main",
        ["lunch", "dinner"],
        "external:restaurant_website:main",
      ),
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
    ).toEqual(["main", "restaurant-main"]);
  });
});
