import { describe, expect, it } from "vitest";

import { mealConsumptionPath } from "./mealConsumptionClient";

describe("meal consumption API path", () => {
  it("encodes every scoped identifier", () => {
    expect(
      mealConsumptionPath("family/id", "meal/id", "person/id", "serving/id"),
    ).toBe(
      "/api/families/family%2Fid/meal-plan/meal%2Fid/participants/person%2Fid/servings/serving%2Fid/consumption",
    );
  });
});
