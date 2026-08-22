import { describe, expect, it } from "vitest";

import { familyPantryPath, familyShoppingListPath } from "./pantryShoppingClient";

describe("pantry and shopping API paths", () => {
  it("builds an encoded pantry path", () => {
    expect(familyPantryPath("family/id")).toBe("/api/families/family%2Fid/pantry");
  });

  it("adds the inactive pantry filter only when requested", () => {
    expect(familyPantryPath("family/id", true)).toBe(
      "/api/families/family%2Fid/pantry?include_inactive=true",
    );
  });

  it("builds an encoded shopping-list path", () => {
    expect(familyShoppingListPath("family/id")).toBe(
      "/api/families/family%2Fid/shopping-list",
    );
  });
});
