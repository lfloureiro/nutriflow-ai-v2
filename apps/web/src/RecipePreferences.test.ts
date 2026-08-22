import { describe, expect, it } from "vitest";

import { recipePreferencesPath } from "./api/recipePreferenceClient";

describe("recipe preference paths", () => {
  it("builds an encoded Family recipe preference path", () => {
    expect(recipePreferencesPath("family id", "recipe/id")).toBe(
      "/api/families/family%20id/recipes/recipe%2Fid/preferences",
    );
  });
});
