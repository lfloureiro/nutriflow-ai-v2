import {expect,test} from "@playwright/test";

const API="http://127.0.0.1:8000/api";

/** All data belong to the temporary PostgreSQL database of the CI job. */
test("weekly map remains usable from desktop through 200% equivalent narrow viewport in both themes", async ({page,request})=>{
  const response=await request.post(`${API}/families`,{data:{
    name:"Família Sintética Responsividade",timezone:"Europe/Lisbon",
    meal_discovery_sources:["shared_recipes"],delivery_address:null,restaurant_area:null,
  }});
  expect(response.ok()).toBe(true);
  const family=await response.json() as {id:string};
  // The hero intentionally requires at least one family member; seed a fictional one.
  const personResponse = await request.post(`${API}/families/${family.id}/persons`,{data:{
    first_name:"Pessoa Visual QA",last_name:null,birth_date:null,
    preferred_locale:"pt-PT",timezone:"Europe/Lisbon",meal_discovery:null,
  }});
  expect(personResponse.ok()).toBe(true);
  await page.addInitScript(id=>{
    window.localStorage.setItem("nutriflow-family-id",id);
    window.localStorage.setItem("nutriflow-locale","pt-PT");
    window.localStorage.setItem("nutriflow-appearance","dark");
  },family.id);
  await page.goto("/#/meals?date=2026-11-20&mode=week");
  await expect(page.locator(".nf-next-meal-hero")).toBeVisible();

  for(const width of [1440,1024,768,390,720]){
    await page.setViewportSize({width,height:900});
    await expect(page.locator(".nf-next-meal-hero")).toBeVisible();
    await expect(page.locator(".weekly-day-grid")).toBeVisible();
    for(const theme of ["dark","light"] as const){
      await page.locator(".nf-appearance").selectOption(theme);
      await expect(page.locator("html")).toHaveAttribute("data-theme",theme);
      const measured=await page.evaluate(()=>{
        const doc=document.documentElement;
        const sidebar=document.querySelector<HTMLElement>(".side-nav");
        const bottom=document.querySelector<HTMLElement>(".bottom-nav");
        const grid=document.querySelector<HTMLElement>(".weekly-day-grid");
        return {
          scrollWidth:doc.scrollWidth,clientWidth:doc.clientWidth,
          sidebar:sidebar?getComputedStyle(sidebar).display:"missing",
          bottom:bottom?getComputedStyle(bottom).display:"missing",
          grid:grid?getComputedStyle(grid).display:"missing",
        };
      });
      expect(measured.scrollWidth,`Horizontal document overflow at ${width}px, ${theme}`).toBeLessThanOrEqual(measured.clientWidth+1);
      expect(measured.grid).not.toBe("none");
      if(width<=760){
        expect(measured.sidebar).toBe("none");
        expect(measured.bottom).not.toBe("none");
      }else{
        expect(measured.sidebar).not.toBe("none");
        expect(measured.bottom).toBe("none");
      }
    }
  }

  // At normal desktop heights the whole 7×4 map, including the last dinner
  // row, should remain above the browser bottom without document scrolling.
  for (const {width,height} of [{width:1440,height:900},{width:1440,height:760},{width:1229,height:610}]) {
    await page.setViewportSize({width,height});
    await page.locator(".nf-appearance").selectOption("dark");
    await expect(page.locator(".nf-week-map-final .weekly-day-grid")).toBeVisible();
    if (height === 610) {
      // The old 700px media threshold ignored the user's short CSS viewport.
      // The grid must now detect and use the actual spare space itself.
      await expect.poll(async () => page.locator(".nf-week-map-final .weekly-day-grid")
        .evaluate(element => (element as HTMLElement).style.getPropertyValue("--week-compact-row")))
        .not.toBe("");
    }
    const fit = await page.evaluate(() => {
      const grid=document.querySelector<HTMLElement>(".nf-week-map-final .weekly-day-grid");
      const hero=document.querySelector<HTMLElement>(".nf-next-meal-hero");
      const nav=document.querySelector<HTMLElement>(".family-meals-date-nav");
      if(!grid||!hero||!nav)throw new Error("Missing week sections");
      return {
        gridBottom:grid.getBoundingClientRect().bottom,
        heroBottom:hero.getBoundingClientRect().bottom,
        navTop:nav.getBoundingClientRect().top,
        clientHeight:document.documentElement.clientHeight,
        gridTop:grid.getBoundingClientRect().top,
        gridRows:getComputedStyle(grid).gridTemplateRows,
        heroHeight:hero.getBoundingClientRect().height,
      };
    });
    // At 100% Chrome zoom text density must match the approved 80%-zoom
    // comparison without shrinking the browser itself.
    const type = await page.evaluate(() => {
      const px = (selector: string) => {
        const element = document.querySelector<HTMLElement>(selector);
        if (!element) throw new Error(`Missing typography selector ${selector}`);
        return Number.parseFloat(getComputedStyle(element).fontSize);
      };
      return {
        navigation: px(".primary-nav .nav-item:not(.active)"),
        brand: px(".nf-brand-name"),
        hero: px(".nf-next-meal-hero h2"),
        meal: px(".nf-week-map-final .nf-week-empty-action"),
        day: px(".nf-week-map-final .weekly-grid-day__date-button small"),
      };
    });
    expect(type.navigation).toBeLessThanOrEqual(16);
    expect(type.brand).toBeLessThanOrEqual(24);
    expect(type.hero).toBeLessThanOrEqual(22);
    expect(type.meal).toBeLessThanOrEqual(12);
    expect(type.day).toBeLessThanOrEqual(21);
    const rowHeights = fit.gridRows.split(" ").map(Number.parseFloat).filter(Number.isFinite);
    // The full-size display gets modestly taller meal cards, while 610px
    // stays in its previously validated compact regime.
    expect(rowHeights.length).toBe(5);
    const mealRows = rowHeights.slice(1);
    // Prevent silent fallback to content-sized rows if CSS calc is rejected.
    if (height === 760) {
      expect(Math.min(...mealRows)).toBeGreaterThanOrEqual(91);
      const computedVariable = await page.locator(".nf-week-map-final .weekly-day-grid").evaluate(element =>
        getComputedStyle(element).getPropertyValue("--week-compact-row").trim()
      );
      expect(computedVariable).toMatch(/(?:px|dvh|clamp)/);
    }
    if (height === 900) expect(Math.min(...mealRows)).toBeGreaterThanOrEqual(118);
    if (height === 610) expect(Math.max(...mealRows)).toBeLessThanOrEqual(66);
    expect(fit.heroBottom).toBeLessThan(fit.navTop);
    expect(fit.gridBottom,`Last dinner row exceeds ${height}px viewport`).toBeLessThanOrEqual(fit.clientHeight-4);
    await page.screenshot({path:`test-results/visual-week-fit-dark-${width}x${height}.png`,fullPage:false});
  }

});
