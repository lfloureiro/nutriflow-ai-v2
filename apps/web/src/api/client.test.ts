import { describe, expect, it } from "vitest";

import {
  buildApiUrl,
  familyDashboardPath,
  familyMealDetailPath,
  familyMealsPath,
  normalizeApiBaseUrl,
  planningBootstrapPath,
} from "./client";

describe("API URL construction", () => {
  it("removes trailing slashes from an explicit API base URL", () => {
    expect(normalizeApiBaseUrl(" https://api.example.test/// ")).toBe(
      "https://api.example.test",
    );
  });

  it("uses same-origin paths when no API base URL is configured", () => {
    expect(buildApiUrl("api/health", "")).toBe("/api/health");
  });

  it("joins an explicit API base URL and path without duplicate slashes", () => {
    expect(buildApiUrl("/api/health", "https://api.example.test/")).toBe(
      "https://api.example.test/api/health",
    );
  });

  it("builds a family dashboard path with an optional date", () => {
    expect(familyDashboardPath("family/id", "2026-08-22")).toBe(
      "/api/families/family%2Fid/dashboard?on_date=2026-08-22",
    );
    expect(familyDashboardPath("family/id")).toBe("/api/families/family%2Fid/dashboard");
  });

  it("builds family meal range and detail paths", () => {
    expect(familyMealsPath("family/id", "2026-08-22", 7)).toBe(
      "/api/families/family%2Fid/meals?days=7&start_date=2026-08-22",
    );
    expect(familyMealsPath("family/id", undefined, 1)).toBe(
      "/api/families/family%2Fid/meals?days=1",
    );
    expect(familyMealDetailPath("family/id", "meal/id")).toBe(
      "/api/families/family%2Fid/meals/meal%2Fid",
    );
  });

  it("encodes the planning instant in the bootstrap query", () => {
    expect(planningBootstrapPath("person/id", "2026-08-22T11:30:00+01:00")).toBe(
      "/api/persons/person%2Fid/planning-bootstrap?scheduled_at=2026-08-22T11%3A30%3A00%2B01%3A00",
    );
  });
});
