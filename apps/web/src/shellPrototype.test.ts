import { describe, expect, it } from "vitest";
// @ts-expect-error Node types are not in the browser-only TypeScript project.
import { readFileSync } from "node:fs";

// Read source files from disk: Vitest can transform ?raw CSS imports to empty strings.
const source = (name: string) => readFileSync(new URL(name, import.meta.url), "utf8");
const baseShell = source("./shell.css");
const prototypeShell = source("./shell-prototype.css");
const screenReference = source("./screen-reference.css");
const prototypeTokens = source("./design-tokens.css");
const main = source("./main.tsx");

describe("Casa à Mesa shared visual shell", () => {
  it("does not customize global navigation, family tile or topbar for the weekly route", () => {
    expect(baseShell).not.toMatch(/\.app-shell--meals\s+\.(?:side-nav|primary-nav|nav-item|shell-topbar)/);
    expect(prototypeShell).not.toContain("app-shell--meals");
  });

  it("loads the same final shell for every route", () => {
    const shellImport = main.indexOf('import "./shell-prototype.css";');
    const screensImport = main.indexOf('import "./screen-reference.css";');
    expect(shellImport).toBeGreaterThan(-1);
    expect(screensImport).toBeGreaterThan(shellImport);
    expect(main.trimEnd().endsWith('import "./screen-reference.css";')).toBe(true);
    expect(screenReference).not.toContain(".side-nav");
    expect(screenReference).not.toContain(".primary-nav");
    expect(screenReference).not.toContain(".nf-week-map-final");
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
