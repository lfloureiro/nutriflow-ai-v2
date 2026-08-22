import { describe, expect, it } from "vitest";

import type { PlanningCandidate } from "./api/types";
import {
  recommendationCandidates,
  recommendationDates,
  recommendationSourceKinds,
} from "./recommendationPlanning";

function candidate(
  kind: "food_item" | "recipe",
  category: string,
  id: string,
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
  };
}

describe("recommendation planning helpers", () => {
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

  it("maps the product source choices to backend channels", () => {
    expect(recommendationSourceKinds(["cooked", "delivery", "restaurant"])).toEqual([
      "home",
      "delivery",
      "restaurant",
    ]);
  });

  it("uses recipes for cooked meals and dishes for commercial sources", () => {
    const candidates = [
      candidate("recipe", "recipe", "recipe-1"),
      candidate("food_item", "dish", "dish-1"),
      candidate("food_item", "ingredient", "ingredient-1"),
    ];

    expect(
      recommendationCandidates(candidates, ["cooked", "delivery"]).map(
        (item) => item.composition_id,
      ),
    ).toEqual(["recipe-1", "dish-1"]);
  });
});
