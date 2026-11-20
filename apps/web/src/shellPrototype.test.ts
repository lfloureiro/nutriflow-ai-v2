import { describe, expect, it } from "vitest";
import baseShell from "./shell.css?raw";
import prototypeShell from "./shell-prototype.css?raw";
import prototypeTokens from "./design-tokens.css?raw";
import main from "./main.tsx?raw";

describe("Casa à Mesa shared visual shell", () => {
  it("does not customize global navigation, family tile or topbar for the weekly route", () => {
    expect(baseShell).not.toMatch(/\.app-shell--meals\s+\.(?:side-nav|primary-nav|nav-item|shell-topbar)/);
    expect(prototypeShell).not.toContain("app-shell--meals");
  });

  it("loads the same final shell for every route", () => {
    expect(main.trimEnd().endsWith('import "./shell-prototype.css";')).toBe(true);
    for (const selector of [".side-nav", ".primary-nav .nav-item", ".side-nav__ai", ".side-nav__family", ".shell-topbar"]) {
      expect(prototypeShell).toContain(selector);
    }
    expect(prototypeShell).toContain("width: 230px");
    expect(prototypeShell).toContain("min-height: 92px");
  });

  it("retains the original light/dark palette and typography", () => {
    for (const color of ["#f6f5f0", "#fffefa", "#25372d", "#285a40", "#19191b", "#222225", "#f1eeea", "#d8b28c"]) {
      expect(prototypeTokens).toContain(color);
    }
    expect(prototypeShell).toContain('"DM Sans"');
    expect(prototypeShell).toContain('"Manrope"');
  });
});
