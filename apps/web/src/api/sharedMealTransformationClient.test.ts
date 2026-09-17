import { describe, expect, it } from "vitest";

import { sharedMealTransformationPath } from "./sharedMealTransformationClient";

describe("shared meal transformation path", () => {
  it("encodes the Family identifier", () => {
    expect(sharedMealTransformationPath("family/id")).toBe(
      "/api/families/family%2Fid/meal-transformations/proposals",
    );
  });
});
