import { describe, expect, it } from "vitest";

import {
  sharedMealTransformationPath,
  sharedMealTransformationPlanPath,
} from "./sharedMealTransformationClient";

describe("shared meal transformation paths", () => {
  it("encodes the Family identifier for proposal preview", () => {
    expect(sharedMealTransformationPath("family/id")).toBe(
      "/api/families/family%2Fid/meal-transformations/proposals",
    );
  });

  it("encodes the Family identifier for transformation planning", () => {
    expect(sharedMealTransformationPlanPath("family/id")).toBe(
      "/api/families/family%2Fid/meal-transformations/plan",
    );
  });
});
