import { describe, expect, it } from "vitest";

import type { MealDiscoveryCapability } from "./api/setupTypes";
import { restaurantCapabilityMessage } from "./RestaurantDiscoveryScreen";

function capability(
  status: MealDiscoveryCapability["status"],
): MealDiscoveryCapability {
  return {
    source: "restaurants",
    selected: true,
    supported: status !== "disabled",
    live: status === "ready",
    status,
    detail: "test",
    credentials_configured: null,
    access_enabled: null,
    adapter_available: null,
  };
}

describe("restaurant capability messaging", () => {
  it("explains ready live discovery", () => {
    expect(restaurantCapabilityMessage(capability("ready"), "pt-PT")).toBe(
      "Pesquisa live configurada",
    );
  });

  it("explains that a missing family area can be overridden in the search", () => {
    expect(restaurantCapabilityMessage(capability("needs_configuration"), "pt-PT")).toContain(
      "escrever uma área nesta pesquisa",
    );
  });

  it("explains disabled discovery without exposing an HTTP error", () => {
    expect(restaurantCapabilityMessage(capability("disabled"), "pt-PT")).toBe(
      "A pesquisa live de restaurantes está desativada nesta instalação.",
    );
  });
});
