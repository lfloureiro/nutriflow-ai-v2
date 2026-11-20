import { expect, test } from "@playwright/test";

/**
 * Route-independent shell invariants, validated in Chromium with the isolated
 * synthetic PostgreSQL service from ux-e2e.yml. No personal data is read.
 */
const API = "http://127.0.0.1:8000/api";

const routes = [
  ["#/home", "Início"],
  ["#/meals?date=2026-11-20&mode=week", "A nossa semana"],
  ["#/house?tab=recipes", "Receitas"],
  ["#/people", "Família"],
  ["#/shopping", "Compras"],
  ["#/house?tab=pantry", "Despensa"],
] as const;

type ShellSnapshot = {
  sidebar: { width: number; background: string; padding: string; border: string };
  brand: { family: string; size: string; weight: string; color: string };
  nav: { family: string; size: string; weight: string; radius: string; padding: string };
  ai: { background: string; radius: string; border: string; padding: string };
  family: { background: string; padding: string };
  header: { background: string; height: number; border: string };
};

async function shellSnapshot(page: import("@playwright/test").Page): Promise<ShellSnapshot> {
  return page.evaluate(() => {
    const read = (selector: string) => {
      const element = document.querySelector<HTMLElement>(selector);
      if (!element) throw new Error(`Missing shell selector ${selector}`);
      return {style: getComputedStyle(element), rect: element.getBoundingClientRect()};
    };
    const sidebar = read(".side-nav");
    const brand = read(".nf-brand-name");
    const nav = read(".primary-nav .nav-item:not(.active)");
    const ai = read(".side-nav__ai");
    const family = read(".side-nav__family");
    const header = read(".shell-topbar");
    return {
      sidebar: {
        width: sidebar.rect.width,
        background: sidebar.style.backgroundImage + "/" + sidebar.style.backgroundColor,
        padding: sidebar.style.padding,
        border: sidebar.style.borderRightColor,
      },
      brand: {
        family: brand.style.fontFamily, size: brand.style.fontSize,
        weight: brand.style.fontWeight, color: brand.style.color,
      },
      nav: {
        family: nav.style.fontFamily, size: nav.style.fontSize,
        weight: nav.style.fontWeight, radius: nav.style.borderRadius,
        padding: nav.style.padding,
      },
      ai: {
        background: ai.style.backgroundImage + "/" + ai.style.backgroundColor,
        radius: ai.style.borderRadius, border: ai.style.borderColor, padding: ai.style.padding,
      },
      family: { background: family.style.backgroundColor, padding: family.style.padding },
      header: {
        background: header.style.backgroundImage + "/" + header.style.backgroundColor,
        height: header.rect.height, border: header.style.borderBottomColor,
      },
    };
  });
}

for (const theme of ["light", "dark"] as const) {
  test(`shared sidebar computed styles never depend on the route in ${theme}`, async ({page,request}) => {
    const response = await request.post(`${API}/families`, {data: {
      name:"Família Sintética Estilos",timezone:"Europe/Lisbon",
      meal_discovery_sources:["shared_recipes"],delivery_address:null,restaurant_area:null,
    }});
    expect(response.ok()).toBe(true);
    const family = await response.json() as {id:string};
  // The hero intentionally requires at least one family member; seed a fictional one.
  const personResponse = await request.post(`${API}/families/${family.id}/persons`,{data:{
    first_name:"Pessoa Visual QA",last_name:null,birth_date:null,
    preferred_locale:"pt-PT",timezone:"Europe/Lisbon",meal_discovery:null,
  }});
  expect(personResponse.ok()).toBe(true);
    await page.setViewportSize({width:1280,height:900});
    await page.addInitScript(({id,appearance}) => {
      window.localStorage.setItem("nutriflow-family-id",id);
      window.localStorage.setItem("nutriflow-appearance",appearance);
      window.localStorage.setItem("nutriflow-locale","pt-PT");
    },{id:family.id,appearance:theme});
    await page.goto("/#/home");
    await expect(page.locator(".side-nav")).toBeVisible();
    await expect(page.locator(".primary-nav .nav-item.active")).toHaveText("Início");
    await expect(page.locator("html")).toHaveAttribute("data-theme",theme);
    await page.evaluate(() => document.fonts.ready);
    const baseline = await shellSnapshot(page);
    // Viewport 1280 CSS px must activate the full-size shell even with Windows display scaling.
    expect(baseline.sidebar.width).toBeGreaterThan(250);
    expect(baseline.sidebar.width).toBeLessThan(280);
    expect(baseline.brand.family).toContain("Manrope");
    for (const [hash,label] of routes.slice(1)) {
      await page.evaluate(value => { window.location.hash=value; },hash);
      await expect(page.locator(".primary-nav .nav-item.active")).toHaveText(label);
      expect(await shellSnapshot(page), `Visual shell differs in ${theme} on ${hash}`).toEqual(baseline);
    }
    await page.getByRole("button",{name:/Gerir o espaço:/}).click();
    await expect(page).toHaveURL(/#\/more/);
    expect(await shellSnapshot(page)).toEqual(baseline);
  });
}

test("weekly image never enlarges the hero and the desktop map preserves seven days",async ({page,request}) => {
  const response = await request.post(`${API}/families`, {data: {
    name:"Família Sintética Semana",timezone:"Europe/Lisbon",
    meal_discovery_sources:["shared_recipes"],delivery_address:null,restaurant_area:null,
  }});
  expect(response.ok()).toBe(true);
  const family = await response.json() as {id:string};
  const personResponse = await request.post(`${API}/families/${family.id}/persons`,{data:{
    first_name:"Pessoa Visual Semana",last_name:null,birth_date:null,
    preferred_locale:"pt-PT",timezone:"Europe/Lisbon",meal_discovery:null,
  }});
  expect(personResponse.ok()).toBe(true);
  await page.setViewportSize({width:1440,height:900});
  await page.addInitScript(id => {
    window.localStorage.setItem("nutriflow-family-id",id);
    window.localStorage.setItem("nutriflow-appearance","dark");
  },family.id);
  await page.goto("/#/meals?date=2026-11-20&mode=week");
  const hero=page.locator(".nf-next-meal-hero");
  await expect(hero).toBeVisible();
  const geometry=await hero.evaluate(element=>{
    const rect=element.getBoundingClientRect();
    const art=element.querySelector<HTMLImageElement>(".nf-next-meal-hero__art img");
    return {hero:rect.height,image:art?.getBoundingClientRect().height??0};
  });
  expect(geometry.hero).toBeGreaterThanOrEqual(135);
  expect(geometry.hero).toBeLessThanOrEqual(138);
  expect(geometry.image).toBeLessThanOrEqual(137);
  const week=page.locator(".nf-week-map-final .weekly-day-grid");
  await expect(week).toBeVisible();
  await expect(week.locator(".weekly-grid-day")).toHaveCount(7);
  const columns=await week.evaluate(element=>getComputedStyle(element).gridTemplateColumns.split(" ").filter(Boolean).length);
  expect(columns).toBe(8);

  // Reference-compatible synthetic captures, never a private family session.
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({path:"test-results/visual-week-dark-1440.png",fullPage:true});
  await page.locator(".nf-appearance").selectOption("light");
  await expect(page.locator("html")).toHaveAttribute("data-theme","light");
  await page.screenshot({path:"test-results/visual-week-light-1440.png",fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await expect(page.locator(".nf-week-day-picker")).toBeVisible();
  await page.screenshot({path:"test-results/visual-week-light-mobile-390.png",fullPage:true});
});
