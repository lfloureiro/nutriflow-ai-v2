import { describe, expect, it } from "vitest";

import { buildApiUrl, normalizeApiBaseUrl } from "./client";

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
});
