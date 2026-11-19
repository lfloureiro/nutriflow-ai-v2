import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

// Every test creates fresh fictional records in the temporary CI PostgreSQL service.
// Never point these tests at the local family database or a shared deployment.
const API = "http://127.0.0.1:8000/api";
const DATE = "2026-11-19";

async function postJson<T>(request: APIRequestContext, path: string, data: unknown): Promise<T> {
  const result = await request.post(`${API}${path}`, { data });
  expect(result.ok(), `POST ${path} failed: ${result.status()} ${await result.text()}`).toBeTruthy();
  return await result.json() as T;
}
async function getJson<T>(request: APIRequestContext, path: string): Promise<T> {
  const result = await request.get(`${API}${path}`);
  expect(result.ok(), `GET ${path} failed: ${result.status()}`).toBeTruthy();
  return await result.json() as T;
}
async function seed(request: APIRequestContext) {
  const family = await postJson<{id:string}>(request, "/families", {
    name:"Família Sintética QA",
    timezone:"Europe/Lisbon",
    meal_discovery_sources:["shared_recipes"],
    delivery_address:null,
    restaurant_area:null,
  });
  const person = await postJson<{id:string}>(request, `/families/${family.id}/persons`, {
    first_name:"Pessoa QA",
    last_name:null,
    birth_date:null,
    preferred_locale:"pt-PT",
    timezone:"Europe/Lisbon",
    meal_discovery:null,
  });
  const ingredient = await postJson<{id:string}>(request, `/families/${family.id}/ingredients`, {
    name:"Arroz QA",brand:null,description:null,composition:null,
  });
  const recipe = await postJson<{id:string}>(request, `/families/${family.id}/recipes`, {
    name:"Prato sintético QA",
    description:null,
    suitable_meal_types:["lunch","dinner"],
    yield_quantity:null,yield_unit:null,serving_count:"2",
    ingredients:[{food_item_id:ingredient.id,quantity:"150",unit:"g",preparation:null,notes:null}],
  });
  const meal = await postJson<{id:string}>(request, `/families/${family.id}/meal-plan`, {
    date:DATE,
    meal_type:"dinner",
    local_time:"20:00",
    recipe_id:recipe.id,
    participants:[{person_id:person.id,quantity:"1",unit:"serving"}],
    location:null,notes:null,
  });
  return { family,person,ingredient,recipe,meal };
}
async function openFamily(page:Page,familyId:string,route:string){
  await page.addInitScript((id:string)=>{
    window.localStorage.setItem("nutriflow-family-id",id);
    window.localStorage.setItem("nutriflow-locale","pt-PT");
  },familyId);
  await page.goto(route);
}

test("desktop: meal drawer, deep-link, history, focus and persistence", async ({page,request})=>{
  const fixture=await seed(request);
  await page.setViewportSize({width:1440,height:900});
  await openFamily(page,fixture.family.id,`/#/meals?date=${DATE}&meal=dinner&mode=week`);
  const drawer=page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  await expect(drawer).toContainText("Prato sintético QA");
  await expect(drawer).toHaveAttribute("aria-modal","true");
  await expect(page.locator("#root")).toHaveAttribute("inert","");
  await expect(page.getByRole("button",{name:"Fechar detalhe"})).toBeFocused();

  await page.keyboard.press("Escape");
  await expect(drawer).toHaveCount(0);
  await expect(page).not.toHaveURL(/meal=dinner/);
  await page.goBack();
  await expect(drawer).toBeVisible();
  await page.reload();
  await expect(drawer).toBeVisible();
  await expect(drawer).toContainText("Prato sintético QA");
  const stored=await getJson<{days:{date:string,slots:{meal_type:string,meals:{id:string}[]}[]}[]}>(request,`/families/${fixture.family.id}/meal-plan?start_date=2026-11-16&days=7`);
  expect(stored.days.find(d=>d.date===DATE)?.slots.find(s=>s.meal_type==="dinner")?.meals.some(m=>m.id===fixture.meal.id)).toBe(true);
});

test("mobile: drawer remains within viewport in both themes",async ({page,request})=>{
  const fixture=await seed(request);
  await page.setViewportSize({width:390,height:844});
  await openFamily(page,fixture.family.id,`/#/meals?date=${DATE}&meal=dinner&mode=week`);
  const drawer=page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  const width=await drawer.evaluate(element=>element.getBoundingClientRect().width);
  expect(width).toBeLessThanOrEqual(391);
  for (const theme of ["light","dark"]){
    await page.evaluate((selected)=>document.documentElement.setAttribute("data-theme",selected),theme);
    await expect(drawer).toBeVisible();
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
    expect(overflow).toBe(false);
  }
  await page.getByRole("button",{name:"Fechar detalhe"}).click();
  await expect(drawer).toHaveCount(0);
});

test("ingredient: draft warning and optional nutrition persist in isolated database", async ({page,request})=>{
  const fixture=await seed(request);
  await openFamily(page,fixture.family.id,"/#/house?tab=ingredients");
  await page.getByRole("button",{name:/Novo ingrediente/}).click();
  await page.getByLabel("Nome",{exact:true}).fill("Ingrediente de teste sem energia");
  await expect(page.getByText("Alterações por guardar")).toBeVisible();
  page.once("dialog",dialog=>dialog.dismiss());
  await page.getByRole("button",{name:/Voltar aos ingredientes/}).click();
  await expect(page.getByText("Alterações por guardar")).toBeVisible();
  await page.getByRole("button",{name:"Guardar",exact:true}).click();
  await expect(page.getByText("Ingrediente de teste sem energia")).toBeVisible();
  const ingredients=await getJson<{name:string,latest_composition:unknown}[]>(request,`/families/${fixture.family.id}/ingredients`);
  expect(ingredients.find(i=>i.name==="Ingrediente de teste sem energia")?.latest_composition).toBeNull();
  await page.reload();
  await expect(page.getByText("Ingrediente de teste sem energia")).toBeVisible();
});

test("person: switching local tabs does not discard an unsaved condition",async ({page,request})=>{
  const fixture=await seed(request);
  await openFamily(page,fixture.family.id,`/#/people?person=${fixture.person.id}`);
  await page.getByRole("button",{name:"Saúde",exact:true}).click();
  await page.getByRole("button",{name:"Adicionar condição"}).click();
  await page.getByLabel("Nome da condição").fill("Condição sintética");
  await page.getByLabel(/Código estável/).fill("qa-condition");
  page.once("dialog",dialog=>dialog.dismiss());
  await page.getByRole("button",{name:"Nutrição",exact:true}).click();
  await expect(page.getByText("Alterações por guardar")).toBeVisible();
  page.once("dialog",dialog=>dialog.accept());
  await page.getByRole("button",{name:"Nutrição",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Nutrição",exact:true})).toBeVisible();
});

test("drawer keyboard focus remains trapped and returns to the underlying page",async ({page,request})=>{
  const fixture=await seed(request);
  await page.setViewportSize({width:1024,height:768});
  await openFamily(page,fixture.family.id,`/#/meals?date=${DATE}&mode=week`);
  const slot=page.getByRole("button",{name:/Prato sintético QA/}).first();
  await expect(slot).toBeVisible();
  await slot.focus();
  await slot.click();
  const dialog=page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  const close=dialog.getByRole("button",{name:"Fechar detalhe"});
  await expect(close).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  const shiftTabInside=await page.evaluate(()=>Boolean(document.activeElement?.closest('[role="dialog"]')));
  expect(shiftTabInside).toBe(true);
  await page.keyboard.press("Tab");
  await expect(close).toBeFocused();
  for(let i=0;i<12;i++){
    await page.keyboard.press("Tab");
    const focusStillInside=await page.evaluate(()=>Boolean(document.activeElement?.closest('[role="dialog"]')));
    expect(focusStillInside).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(page.locator("#root")).not.toHaveAttribute("inert","");
  await expect(slot).toBeFocused();
});

test("weekly planner and drawer have no horizontal overflow across four responsive widths and both themes",async ({page,request})=>{
  const fixture=await seed(request);
  await page.emulateMedia({reducedMotion:"reduce"});
  for(const width of [1440,1024,768,390]){
    await page.setViewportSize({width,height:900});
    for(const theme of ["light","dark"]){
      await openFamily(page,fixture.family.id,`/#/meals?date=${DATE}&meal=dinner&mode=week`);
      await page.evaluate(value=>window.localStorage.setItem("nutriflow-appearance",value),theme);
      await page.reload();
      const dialog=page.getByRole("dialog");
      await expect(dialog).toBeVisible();
      await expect(page.locator("html")).toHaveAttribute("data-theme",theme);
      const geometry=await page.evaluate(()=>{
        const drawer=document.querySelector('[role="dialog"]');
        if(!drawer)throw new Error("Missing meal drawer");
        const rect=drawer.getBoundingClientRect();
        return {
          viewport:window.innerWidth,
          document:document.documentElement.scrollWidth,
          body:document.body.scrollWidth,
          drawerRight:rect.right,
          drawerLeft:rect.left,
          drawerClient:drawer.clientWidth,
          drawerScroll:drawer.scrollWidth,
        };
      });
      expect(geometry.document, `document overflow at ${width}px / ${theme}`).toBeLessThanOrEqual(geometry.viewport+1);
      expect(geometry.drawerRight,`drawer clipped at ${width}px / ${theme}`).toBeLessThanOrEqual(geometry.viewport+1);
      expect(geometry.drawerLeft).toBeGreaterThanOrEqual(-1);
      expect(geometry.drawerScroll,`drawer content overflow at ${width}px / ${theme}`).toBeLessThanOrEqual(geometry.drawerClient+2);
      await page.getByRole("button",{name:"Fechar detalhe"}).click();
      await expect(dialog).toHaveCount(0);
    }
  }
});
