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
    // The first follow-up screen should now use the same common tokens as
    // the remaining routes, without altering the approved weekly layout.
    const home = await page.evaluate(() => {
      const hero = document.querySelector<HTMLElement>(".nf-meal-hero");
      const heading = document.querySelector<HTMLElement>(".nf-home-heading h1");
      if (!hero || !heading) throw new Error("Missing homepage design surfaces");
      const art = getComputedStyle(hero);
      return {
        radius: art.borderRadius,
        minHeight: parseFloat(art.minHeight),
        fontFamily: getComputedStyle(heading).fontFamily,
        screenWidth: document.documentElement.scrollWidth,
        viewportWidth: document.documentElement.clientWidth,
      };
    });
    expect(home.radius).toBe("17px");
    expect(home.minHeight).toBeLessThanOrEqual(165);
    expect(home.fontFamily).toContain("Manrope");
    expect(home.screenWidth).toBeLessThanOrEqual(home.viewportWidth + 1);
    const density = await page.evaluate(() => {
      const tiles = document.querySelectorAll<HTMLElement>(".nf-home .nf-day-slot");
      const hero = document.querySelector<HTMLElement>(".nf-home .nf-meal-hero");
      const screen = document.querySelector<HTMLElement>(".nf-home");
      return {
        meals: tiles.length,
        cardHeight: tiles[0]?.getBoundingClientRect().height ?? 0,
        heroHeight: hero?.getBoundingClientRect().height ?? 0,
        screenWidth: screen?.getBoundingClientRect().width ?? 0,
      };
    });
    expect(density.meals).toBe(4);
    expect(density.cardHeight).toBeLessThanOrEqual(180);
    expect(density.heroHeight).toBeLessThanOrEqual(260);
    const arrangement=await page.evaluate(() => {
      const root=document.querySelector<HTMLElement>(".nf-home");
      const hero=document.querySelector<HTMLElement>(".nf-meal-hero");
      const day=document.querySelector<HTMLElement>(".nf-today-section");
      const family=document.querySelector<HTMLElement>(".nf-family-panel");
      if(!root || !hero || !day || !family)throw new Error("Missing Home reference sections");
      return {
        template:getComputedStyle(root).gridTemplateAreas,
        heroWidth:hero.getBoundingClientRect().width,
        rootWidth:root.getBoundingClientRect().width,
        dayTop:day.getBoundingClientRect().top,
        familyTop:family.getBoundingClientRect().top,
        heroBottom:hero.getBoundingClientRect().bottom
      };
    });
    expect(arrangement.template).toContain("hero hero");
    expect(arrangement.heroWidth).toBeGreaterThan(arrangement.rootWidth-2);
    expect(arrangement.dayTop).toBeGreaterThanOrEqual(arrangement.heroBottom);
    expect(Math.abs(arrangement.dayTop-arrangement.familyTop)).toBeLessThanOrEqual(4);
    await page.screenshot({path:`test-results/visual-home-${theme}-1280.png`,fullPage:true});

    const footerGeometry = await page.evaluate(() => {
      const footer = document.querySelector<HTMLElement>(".side-nav__family");
      const ai = document.querySelector<HTMLElement>(".side-nav__ai");
      const avatar = footer?.querySelector<HTMLElement>(".side-nav__family-avatar");
      const copy = footer?.querySelector<HTMLElement>(".side-nav__family-copy");
      const title = copy?.querySelector<HTMLElement>("strong");
      const subtitle = copy?.querySelector<HTMLElement>("small");
      if (!footer || !ai || !avatar || !copy || !title || !subtitle) throw new Error("Missing family footer pieces");
      const f=footer.getBoundingClientRect(),aiRect=ai.getBoundingClientRect(),a=avatar.getBoundingClientRect(),
        c=copy.getBoundingClientRect(),t=title.getBoundingClientRect(),s=subtitle.getBoundingClientRect();
      return {
        aligned: a.right+6 <= c.left,
        vertical: t.bottom <= s.top,
        contained: a.left >= f.left-1 && s.right <= f.right+1 && s.bottom <= f.bottom+1,
        visible: f.bottom <= window.innerHeight+1 && f.top >= 0,
        bottomGap: window.innerHeight - f.bottom,
        pairGap: f.top - aiRect.bottom,
        avatarFont: getComputedStyle(avatar).fontSize,
        subtitleFont: getComputedStyle(subtitle).fontSize,
        subtitleCase: getComputedStyle(subtitle).textTransform,
      };
    });
    expect(footerGeometry.aligned).toBe(true);
    expect(footerGeometry.vertical).toBe(true);
    expect(footerGeometry.contained).toBe(true);
    expect(footerGeometry.visible).toBe(true);
    expect(footerGeometry.bottomGap).toBeGreaterThanOrEqual(0);
    expect(footerGeometry.bottomGap).toBeLessThanOrEqual(40);
    expect(footerGeometry.pairGap).toBeGreaterThanOrEqual(0);
    expect(footerGeometry.pairGap).toBeLessThanOrEqual(32);
    expect(footerGeometry.subtitleCase).toBe("none");

    // Viewport 1280 CSS px must activate the full-size shell even with Windows display scaling.
    expect(baseline.sidebar.width).toBeGreaterThan(250);
    expect(baseline.sidebar.width).toBeLessThan(280);
    expect(baseline.brand.family).toContain("Manrope");
    for (const [hash,label] of routes.slice(1)) {
      await page.evaluate(value => { window.location.hash=value; },hash);
      await expect(page.locator(".primary-nav .nav-item.active")).toHaveText(label);
      expect(await shellSnapshot(page), `Visual shell differs in ${theme} on ${hash}`).toEqual(baseline);
      if (hash.includes("people")) {
        await expect(page.locator(".nf-family-main-grid")).toBeVisible();
        await expect(page.locator(".nf-family-member-section .person-row")).toHaveCount(1);
        await expect(page.locator(".nf-family-objectives")).toBeVisible();
        await expect(page.locator(".nf-family-preferences")).toBeVisible();
        await expect(page.locator(".nf-family-comparison")).toBeVisible();
      }
      if (hash.includes("shopping")) {
        await expect(page.locator(".nf-shopping-overview > div")).toHaveCount(4);
      }
      if (hash.includes("pantry")) {
        await expect(page.locator(".nf-pantry-summary > div")).toHaveCount(4);
      }
      if (!hash.includes("meals")) {
        await expect(page.locator(".home-base, .shopping-screen, .people-screen").first()).toBeVisible();
        await expect(page.locator(".shell-main .shell-loading")).toHaveCount(0);
        await expect(page.locator(".shell-main")).not.toContainText("A carregar o dia da família");
        const screenId=hash.includes("shopping") ? "shopping" : hash.includes("people") ? "family" :
          hash.includes("pantry") ? "pantry" : "recipes";
        await page.screenshot({path:`test-results/visual-screen-${screenId}-${theme}-1280.png`,fullPage:true});
      }
      if (hash.includes("house") || hash.includes("shopping") || hash.includes("people")) {
        await expect(page.locator(".home-base, .shopping-screen, .people-screen").first()).toBeVisible();
        const surface = await page.evaluate(() => {
          const root=document.querySelector<HTMLElement>(".home-base, .shopping-screen, .people-screen");
          if(!root) throw new Error("Missing secondary route root");
          return getComputedStyle(document.documentElement).getPropertyValue("--nf-screen-card-radius").trim();
        });
        expect(surface).toBe("18px");
      }
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
    window.localStorage.setItem("nutriflow-locale","pt-PT");
  },family.id);
  await page.goto("/#/meals?date=2026-11-20&mode=week");
  const hero=page.locator(".nf-next-meal-hero");
  await expect(hero).toBeVisible();
  const geometry=await hero.evaluate(element=>{
    const rect=element.getBoundingClientRect();
    const art=element.querySelector<HTMLImageElement>(".nf-next-meal-hero__art img");
    const info=element.querySelector<HTMLElement>(".nf-next-meal-hero__info")?.getBoundingClientRect();
    return {hero:rect.height,image:art?.getBoundingClientRect().height??0,
      infoBottom:info?.bottom??0,heroBottom:rect.bottom, infoTop:info?.top??0, heroTop:rect.top};
  });
  expect(geometry.hero).toBeGreaterThanOrEqual(100);
  expect(geometry.hero).toBeLessThanOrEqual(250);
  expect(geometry.image).toBeLessThanOrEqual(geometry.hero+1);
  expect(geometry.infoTop).toBeGreaterThanOrEqual(geometry.heroTop);
  expect(geometry.infoBottom).toBeLessThanOrEqual(geometry.heroBottom+1);
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

test("home fits a 1280 × 700 browser viewport with four real profile cards",async({page,request})=>{
  const response=await request.post(`${API}/families`,{data:{
    name:"Casa Visual Compacta",timezone:"Europe/Lisbon",
    meal_discovery_sources:["shared_recipes"],delivery_address:null,restaurant_area:null,
  }});
  expect(response.ok()).toBe(true);
  const family=await response.json() as {id:string};
  for(let i=1;i<=4;i++){
    const person=await request.post(`${API}/families/${family.id}/persons`,{data:{
      first_name:`Pessoa Visual ${i}`,last_name:null,birth_date:null,
      preferred_locale:"pt-PT",timezone:"Europe/Lisbon",meal_discovery:null,
    }});
    expect(person.ok()).toBe(true);
  }
  await page.setViewportSize({width:1280,height:700});
  await page.addInitScript(id=>{
    localStorage.setItem("nutriflow-family-id",id);
    localStorage.setItem("nutriflow-appearance","dark");
    localStorage.setItem("nutriflow-locale","pt-PT");
  },family.id);
  await page.goto("/#/home");
  await expect(page.locator(".nf-home .nf-day-slot")).toHaveCount(4);
  await expect(page.locator(".nf-home .nf-person-line")).toHaveCount(4);
  await page.evaluate(()=>document.fonts.ready);
  const geometry=await page.evaluate(()=>{
    const root=document.querySelector<HTMLElement>(".nf-home")!;
    const items=[...root.querySelectorAll<HTMLElement>(".nf-home-heading,.nf-meal-hero,.nf-today-section,.nf-home-shortcuts,.nf-saved-weeks,.nf-home-note")];
    const bottom=Math.max(...items.map(el=>el.getBoundingClientRect().bottom));
    return {
      bottom,
      viewport:innerHeight,
      overflowingX:document.documentElement.scrollWidth>document.documentElement.clientWidth+1,
      overflowFamily:getComputedStyle(document.querySelector<HTMLElement>(".nf-family-panel")!).overflowY,
      visibleMemberCount:(()=>{
        const panel=document.querySelector<HTMLElement>(".nf-family-panel")!;
        const r=panel.getBoundingClientRect();
        return [...panel.querySelectorAll<HTMLElement>(".nf-person-line")]
          .filter(item=>{const box=item.getBoundingClientRect();return box.top>=r.top-1 && box.bottom<=r.bottom+1;}).length;
      })(),
    };
  });
  expect(geometry.bottom).toBeLessThanOrEqual(geometry.viewport+2);
  expect(geometry.overflowingX).toBe(false);
  expect(geometry.overflowFamily).toBe("auto");
  expect(geometry.visibleMemberCount).toBeGreaterThanOrEqual(3);
  await page.screenshot({path:"test-results/visual-home-dark-1280x700.png",fullPage:false});
});
