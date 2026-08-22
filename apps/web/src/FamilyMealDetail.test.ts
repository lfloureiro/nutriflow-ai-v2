import { describe, expect, it } from "vitest";

import type { FamilyMealDetailServing } from "./api/familyMealDetailTypes";
import { currentServingEvidence } from "./FamilyMealDetail";

function serving(overrides: Partial<FamilyMealDetailServing> = {}): FamilyMealDetailServing {
  return {
    id: "serving-1",
    item_type: "dish",
    item_name: "Dinner",
    status: "planned",
    quantity_planned: "400.0000",
    quantity_served: null,
    quantity_consumed: null,
    quantity_unit: "g",
    energy_planned_kcal: "560.00",
    energy_served_kcal: null,
    energy_consumed_kcal: null,
    ...overrides,
  };
}

describe("family meal detail serving evidence", () => {
  it("shows planned evidence when no realized serving exists", () => {
    expect(currentServingEvidence(serving())).toEqual({
      stage: "planned",
      quantity: "400.0000",
      energyKcal: "560.00",
    });
  });

  it("prefers consumed evidence over served and planned values", () => {
    expect(
      currentServingEvidence(
        serving({
          status: "consumed",
          quantity_served: "390.0000",
          quantity_consumed: "350.0000",
          energy_served_kcal: "546.00",
          energy_consumed_kcal: "490.00",
        }),
      ),
    ).toEqual({
      stage: "consumed",
      quantity: "350.0000",
      energyKcal: "490.00",
    });
  });
});
