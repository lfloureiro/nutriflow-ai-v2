import {expect, test} from "@playwright/test";

const API="http://127.0.0.1:8000/api";

/** Synthetic PostgreSQL-only fixture: do not touch anyone's real list. */
test("shopping workspace shows live manual items in the correct editorial group",async ({page,request})=>{
  const create=await request.post(`${API}/families`,{data:{
    name:"Família Sintética Compras",timezone:"Europe/Lisbon",
    meal_discovery_sources:["shared_recipes"],delivery_address:null,restaurant_area:null,
  }});
  expect(create.ok()).toBe(true);
  const family=await create.json() as {id:string};
  const item=await request.post(`${API}/families/${family.id}/shopping-list/items`,{data:{
    name:"Arroz sintético para teste",quantity:"2",unit:"kg",
  }});
  expect(item.ok()).toBe(true);
  await page.addInitScript(id=>{
    localStorage.setItem("nutriflow-family-id",id);
    localStorage.setItem("nutriflow-locale","pt-PT");
    localStorage.setItem("nutriflow-appearance","dark");
  },family.id);
  for(const viewport of [{width:1280,height:631},{width:1672,height:941}]){
    await page.setViewportSize(viewport);
    await page.goto("/#/shopping");
    await expect(page.locator(".nf-shopping-workspace")).toBeVisible();
    await expect(page.locator(".nf-shopping-workspace-aside .nf-shopping-aside-card")).toHaveCount(2);
    const group=page.locator(".nf-shopping-item-group").filter({hasText:"Artigos acrescentados"});
    await expect(group).toBeVisible();
    await expect(group.getByText("Arroz sintético para teste")).toBeVisible();
    await expect(page.locator(".nf-shopping-aside-card").first()).toContainText("Por comprar");
    const geometry=await page.evaluate(()=>{
      const main=document.querySelector<HTMLElement>(".nf-shopping-workspace-main")!;
      const aside=document.querySelector<HTMLElement>(".nf-shopping-workspace-aside")!;
      return {
        aligned:Math.abs(main.getBoundingClientRect().top-aside.getBoundingClientRect().top)<3,
        sideBySide:aside.getBoundingClientRect().left>=main.getBoundingClientRect().right-1,
        horizontalOverflow:document.documentElement.scrollWidth>document.documentElement.clientWidth+1,
      };
    });
    expect(geometry.aligned).toBe(true);
    expect(geometry.sideBySide).toBe(true);
    expect(geometry.horizontalOverflow).toBe(false);
    await page.screenshot({path:`test-results/shopping-live-synthetic-${viewport.width}x${viewport.height}.png`,fullPage:false,animations:"disabled"});
  }
});
