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
});
