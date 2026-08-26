import { describe, expect, it } from "vitest";

import {
  mealConsumptionPath,
  mealParticipantConsumptionPath,
} from "./mealConsumptionClient";

describe("meal consumption API path", () => {
  it("encodes every serving-scoped identifier", () => {
    expect(
      mealConsumptionPath("family/id", "meal/id", "person/id", "serving/id"),
    ).toBe(
      "/api/families/family%2Fid/meal-plan/meal%2Fid/participants/person%2Fid/servings/serving%2Fid/consumption",
    );
  });

  it("encodes every participant-scoped identifier", () => {
    expect(
      mealParticipantConsumptionPath("family/id", "meal/id", "person/id"),
    ).toBe(
      "/api/families/family%2Fid/meal-plan/meal%2Fid/participants/person%2Fid/consumption",
    );
  });
});
