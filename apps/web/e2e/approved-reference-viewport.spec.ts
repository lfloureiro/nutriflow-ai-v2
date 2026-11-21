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
      expect(bounds.sidebarWidth).toBeGreaterThanOrEqual(223);
      expect(bounds.sidebarWidth).toBeLessThanOrEqual(225);

      if (destination.id === "familia") {
        await expect(page.locator(".nf-family-comparison-table tbody tr")).toHaveCount(3);
        await expect(page.locator(".nf-family-comparison-table thead th")).toHaveCount(5);
        await expect(page.locator(".nf-family-goal-facts > div")).toHaveCount(3);
      }
      if (destination.id === "receitas") {
        await expect(page.locator(".nf-recipe-browse-toolbar")).toBeVisible();
      }
      if (destination.id === "compras") {
        await expect(page.locator(".nf-shopping-workspace")).toBeVisible();
      }
      if (destination.id === "despensa") {
        await expect(page.locator(".nf-pantry-columns")).toBeVisible();
      }

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
    // Real Windows/Chrome CSS viewport: a narrow, short desktop must keep
    // the same two-column composition rather than turning into a giant feed.
    await page.setViewportSize({width:1229,height:610});
    await page.goto("/#/home");
    await expect(page.locator(".nf-home .nf-day-slot")).toHaveCount(4);
    const compact=await page.evaluate(()=>{
      const home=document.querySelector<HTMLElement>(".nf-home")!;
      const hero=document.querySelector<HTMLElement>(".nf-home .nf-meal-hero")!;
      const today=document.querySelector<HTMLElement>(".nf-home .nf-today-section")!;
      const members=document.querySelector<HTMLElement>(".nf-home .nf-family-panel")!;
      const weeks=document.querySelector<HTMLElement>(".nf-home .nf-saved-weeks")!;
      return {
        fullWidth:document.documentElement.scrollWidth,
        windowWidth:document.documentElement.clientWidth,
        homeBottom:home.getBoundingClientRect().bottom,
        heroHeight:hero.getBoundingClientRect().height,
        aligned:Math.abs(today.getBoundingClientRect().top-members.getBoundingClientRect().top)<5,
        weekVisible:weeks.getBoundingClientRect().bottom<=innerHeight+2,
      };
    });
    expect(compact.fullWidth).toBeLessThanOrEqual(compact.windowWidth+1);
    expect(compact.homeBottom).toBeLessThanOrEqual(612);
    expect(compact.heroHeight).toBeLessThanOrEqual(110);
    expect(compact.aligned).toBe(true);
    expect(compact.weekVisible).toBe(true);
    await page.screenshot({path:`test-results/reference-inicio-${appearance}-1229x610.png`,fullPage:false,animations:"disabled"});
    // Actual user environment: 1280x631 CSS px. Verify the four
    // controls/three week cards no longer fall back to grey UA buttons.
    await page.setViewportSize({width:1280,height:631});
    await page.goto("/#/home");
    await expect(page.locator(".nf-home-shortcut-grid > button")).toHaveCount(4);
    await expect(page.locator(".nf-home-week-cards > button")).toHaveCount(3);
    const homeContent = await page.evaluate(() => {
      const shortcut = [...document.querySelectorAll<HTMLElement>(".nf-home-shortcut-grid > button")];
      const weeks = [...document.querySelectorAll<HTMLElement>(".nf-home-week-cards > button")];
      return {
        shortcutRows: new Set(shortcut.map(el=>Math.round(el.getBoundingClientRect().top))).size,
        weekRows: new Set(weeks.map(el=>Math.round(el.getBoundingClientRect().top))).size,
        background: getComputedStyle(shortcut[0]!).backgroundColor,
        horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      };
    });
    const outerShortcutDisplay = await page.locator(".nf-home .nf-home-shortcuts")
      .evaluate(el=>getComputedStyle(el).display);
    expect(outerShortcutDisplay,"The outer shortcut panel must not be a 2-column grid").toBe("flex");
    expect(homeContent.shortcutRows).toBe(1);
    expect(homeContent.weekRows).toBe(1);
    expect(homeContent.background).not.toBe("rgb(239, 239, 239)");
    expect(homeContent.horizontalOverflow).toBe(false);
    const peopleFit = await page.evaluate(()=>{
      const panel=document.querySelector<HTMLElement>(".nf-home .nf-family-panel");
      const people=[...document.querySelectorAll<HTMLElement>(".nf-home .nf-person-line")];
      return !!panel && people.length===4 && people.every(item=>{
        const rect=item.getBoundingClientRect();
        return rect.bottom <= panel.getBoundingClientRect().bottom+2 &&
          rect.top >= panel.getBoundingClientRect().top-2;
      });
    });
    expect(peopleFit,"All four family rows must be visible without internal scrolling at 1280x631").toBe(true);

    await page.screenshot({path:`test-results/reference-inicio-${appearance}-1280x631.png`,fullPage:false,animations:"disabled"});
    for (const [screen,route,selector] of [
      ["receitas","#/house?tab=recipes",".recipe-catalogue"],
      ["compras","#/shopping",".shopping-screen"],
      ["despensa","#/house?tab=pantry",".pantry-screen"],
    ] as const) {
      await page.goto(`/${route}`);
      await expect(page.locator(selector)).toBeVisible();
      if(screen==="compras") {
        await expect(page.locator(".nf-shopping-overview > div")).toHaveCount(4);
        const listTop=await page.locator(".shopping-list-section").evaluate(el=>el.getBoundingClientRect().top);
        expect(listTop).toBeLessThan(631);

        const cols=await page.locator(".nf-shopping-overview").evaluate(el=>getComputedStyle(el).gridTemplateColumns.split(" ").length);
        expect(cols).toBe(4);
      }
      if(screen==="despensa") {
        await expect(page.locator(".nf-pantry-summary > div")).toHaveCount(4);
        const searchTop=await page.locator(".pantry-screen .nf-list-controls").evaluate(el=>el.getBoundingClientRect().top);
        expect(searchTop).toBeLessThan(631);

        const cols=await page.locator(".nf-pantry-summary").evaluate(el=>getComputedStyle(el).gridTemplateColumns.split(" ").length);
        expect(cols).toBe(4);
      }
      await page.screenshot({path:`test-results/reference-${screen}-${appearance}-1280x631.png`,fullPage:false,animations:"disabled"});
    }
    // Critical regression: a 150% browser zoom can expose a 1024px-wide
    // CSS viewport in an otherwise wide Windows screenshot. The reference
    // layout must not fall back to giant native controls at this width.
    await page.setViewportSize({width:1024,height:505});
    for(const [screen,route,ready] of [
      ["inicio","#/home",".nf-home"],
      ["receitas","#/house?tab=recipes",".recipe-catalogue"],
      ["familia","#/people",".people-screen"],
      ["compras","#/shopping",".shopping-screen"],
      ["despensa","#/house?tab=pantry",".pantry-screen"],
    ] as const){
      await page.goto(`/${route}`);
      await expect(page.locator(ready)).toBeVisible();
      if(screen==="inicio"){
        const rows=await page.locator(".nf-home-shortcut-grid > button").evaluateAll(els=>
          new Set(els.map(el=>Math.round(el.getBoundingClientRect().top))).size);
        const containerDisplay=await page.locator(".nf-home .nf-home-shortcuts")
          .evaluate(el=>getComputedStyle(el).display);
        expect(containerDisplay).toBe("flex");
        expect(rows).toBe(1);
        const weeklyRows=await page.locator(".nf-home-week-cards > button").evaluateAll(els=>
          new Set(els.map(el=>Math.round(el.getBoundingClientRect().top))).size);
        expect(weeklyRows).toBe(1);
      }
      if(screen==="receitas"){
        const height=await page.locator(".nf-recipe-feature").evaluate(el=>el.getBoundingClientRect().height);
        expect(height).toBeLessThanOrEqual(100);
      }
      if(screen==="familia"){
        await expect(page.locator(".nf-family-comparison-table tbody tr")).toHaveCount(3);
        const background=await page.locator(".nf-family-comparison-table thead th button").first()
          .evaluate(el=>getComputedStyle(el).backgroundColor);
        expect(background).toBe("rgba(0, 0, 0, 0)");
      }
      if(screen==="compras"||screen==="despensa"){
        const selector=screen==="compras"?".nf-shopping-overview":".nf-pantry-summary";
        const columns=await page.locator(selector).evaluate(el=>
          getComputedStyle(el).gridTemplateColumns.split(" ").length);
        expect(columns).toBe(4);
      }
      await page.screenshot({path:`test-results/reference-${screen}-${appearance}-1024x505.png`,
        fullPage:false,animations:"disabled"});
    }
  });
}
