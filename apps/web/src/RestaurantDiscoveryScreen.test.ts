import { describe, expect, it } from "vitest";

import type { MealDiscoveryCapability } from "./api/setupTypes";
import { restaurantCapabilityMessage } from "./RestaurantDiscoveryScreen";

function capability(
  status: MealDiscoveryCapability["status"],
  credentialsConfigured: boolean | null = null,
): MealDiscoveryCapability {
  return {
    source: "restaurants",
    selected: true,
    supported: status !== "disabled",
    live: status === "ready",
    status,
    detail: "test",
    credentials_configured: credentialsConfigured,
    access_enabled: null,
    adapter_available: null,
  };
}

describe("restaurant capability messaging", () => {
  it("explains Google quality-ranked discovery", () => {
    expect(restaurantCapabilityMessage(capability("ready", true), "pt-PT")).toContain(
      "Google Places ativo",
    );
  });

  it("explains OpenStreetMap fallback when Google is not configured", () => {
    expect(restaurantCapabilityMessage(capability("ready", false), "pt-PT")).toContain(
      "OpenStreetMap ativo como fallback",
    );
  });

  it("explains that a missing family area can be overridden in the search", () => {
    expect(
      restaurantCapabilityMessage(capability("needs_configuration"), "pt-PT"),
    ).toContain("escrever uma área nesta pesquisa");
  });

  it("explains disabled discovery without exposing an HTTP error", () => {
    expect(restaurantCapabilityMessage(capability("disabled"), "pt-PT")).toBe(
      "A pesquisa live de restaurantes está desativada nesta instalação.",
    );
  });
});
