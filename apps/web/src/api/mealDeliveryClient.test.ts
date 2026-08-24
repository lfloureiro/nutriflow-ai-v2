import { describe, expect, it } from "vitest";

import { mealDeliverySyncPath } from "./mealDeliveryClient";

describe("meal delivery sync path", () => {
  it("encodes the Family identifier and keeps the provider key", () => {
    expect(mealDeliverySyncPath("family/id", "bolt_food")).toBe(
      "/api/families/family%2Fid/meal-discovery/providers/bolt_food/sync",
    );
  });
});
