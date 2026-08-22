import { describe, expect, it } from "vitest";

import { translate } from "./i18n";

describe("web translations", () => {
  it("provides the core recommendation action in both supported locales", () => {
    expect(translate("pt-PT", "planner.recommend")).toBe("Obter recomendações");
    expect(translate("en", "planner.recommend")).toBe("Get recommendations");
  });

  it("keeps product naming stable across locales", () => {
    expect(translate("pt-PT", "app.brand")).toBe("NutriFlow AI");
    expect(translate("en", "app.brand")).toBe("NutriFlow AI");
  });

  it("describes server-authoritative planning discovery in both locales", () => {
    expect(translate("pt-PT", "planner.stateReady")).toBe("Estado diário encontrado");
    expect(translate("en", "planner.stateReady")).toBe("Daily state found");
  });
});
