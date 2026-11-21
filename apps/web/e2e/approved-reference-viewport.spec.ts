import { expect, test } from "@playwright/test";

/**
 * The five approved illustrative mockups have the exact 1672x941 target size
 * (docs/ux/references/manifest.json). These are synthetic browser captures,
 * not claims of pixel parity or screenshots of a real household.
 *
 * The PNG originals still need to be checked into docs/ux/references/ before
 * automatic image comparison can be made authoritative.
 */
const API = "http://127.0.0.1:8000/api";
const viewport = { width: 1672, height: 941 };
const destinations = [
  { id: "inicio", hash: "#/home", ready: ".nf-home" },
  { id: "receitas", hash: "#/house?tab=recipes", ready: ".recipe-catalogue" },
  { id: "familia", hash: "#/people", ready: ".people-screen" },
  { id: "compras", hash: "#/shopping", ready: ".shopping-screen" },
  { id: "despensa", hash: "#/house?tab=pantry", ready: ".pantry-screen" },
] as const;

for (const appearance of ["dark", "light"] as const) {
  test(`approved-reference viewport: five screens, ${appearance}`, async ({ page, request }) => {
    const response = await request.post(`${API}/families`, {
      data: {
        name: "Agregado Sintético Referência",
        timezone: "Europe/Lisbon",
        meal_discovery_sources: ["shared_recipes"],
        delivery_address: null,
        restaurant_area: null,
      },
    });
    expect(response.ok()).toBe(true);
    const family = (await response.json()) as { id: string };
    for (let index = 1; index <= 4; index += 1) {
      const person = await request.post(`${API}/families/${family.id}/persons`, {
        data: {
          first_name: `Pessoa Sintética ${index}`,
          last_name: null,
          birth_date: null,
          preferred_locale: "pt-PT",
          timezone: "Europe/Lisbon",
          meal_discovery: null,
        },
      });
      expect(person.ok()).toBe(true);
    }
    await page.setViewportSize(viewport);
    await page.addInitScript(
      ({ id, theme }) => {
        localStorage.setItem("nutriflow-family-id", id);
        localStorage.setItem("nutriflow-appearance", theme);
        localStorage.setItem("nutriflow-locale", "pt-PT");
      },
      { id: family.id, theme: appearance },
    );
    for (const destination of destinations) {
      await page.goto(`/${destination.hash}`);
      await expect(page.locator(destination.ready).first()).toBeVisible();
      await expect(page.locator("html")).toHaveAttribute("data-theme", appearance);
      await page.evaluate(() => document.fonts.ready);
      await expect(page.locator(".side-nav")).toBeVisible();

      // A reference must use one common sidebar, irrespective of active route.
      const bounds = await page.evaluate(() => ({
        documentWidth: document.documentElement.scrollWidth,
        viewportWidth: document.documentElement.clientWidth,
        sidebarWidth: document.querySelector<HTMLElement>(".side-nav")!.getBoundingClientRect().width,
      }));
      expect(bounds.documentWidth, `${destination.id} horizontal overflow`)
        .toBeLessThanOrEqual(bounds.viewportWidth + 1);
      expect(bounds.sidebarWidth).toBeGreaterThanOrEqual(310);
      expect(bounds.sidebarWidth).toBeLessThanOrEqual(321);

      if (destination.id === "inicio") {
        const layout = await page.locator(".nf-home").evaluate((root) => {
          const content = [...root.querySelectorAll<HTMLElement>(
            ".nf-home-heading,.nf-meal-hero,.nf-today-section,.nf-family-panel,.nf-home-shortcuts,.nf-saved-weeks,.nf-home-note"
          )];
          return {
            bottom: Math.max(...content.map((element) => element.getBoundingClientRect().bottom)),
            viewport: innerHeight,
            memberCount: root.querySelectorAll(".nf-person-line").length,
            familyScroll: getComputedStyle(root.querySelector<HTMLElement>(".nf-family-panel")!).overflowY,
          };
        });
        expect(layout.bottom, "Home primary sections must fit within reference viewport")
          .toBeLessThanOrEqual(layout.viewport + 2);
        expect(layout.memberCount).toBe(4);
        expect(layout.familyScroll).toBe("auto");
      }

      await page.screenshot({
        path: `test-results/reference-${destination.id}-${appearance}-1672x941.png`,
        fullPage: false,
        animations: "disabled",
      });
    }
  });
}
