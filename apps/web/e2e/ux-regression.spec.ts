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
  await drawer.getByText("Restrições por pessoa · fontes desta consulta").click();
  await expect(drawer.getByText(/^Porção registada: /)).toBeVisible();
  await expect(drawer.getByText(/Sem restrições específicas devolvidas nesta consulta/)).toBeVisible();

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

test("weekly day changes preserve the calendar without intermediate loading or plan refetch",async ({page,request})=>{
  const fixture=await seed(request);
  await page.setViewportSize({width:390,height:844});
  await openFamily(page,fixture.family.id,`/#/meals?date=${DATE}&mode=week`);
  const grid=page.locator(".weekly-day-grid");
  await expect(grid).toBeVisible();
  await page.evaluate(()=>{
    const key="nf-week-grid-remounts-qa";
    (window as typeof window & {__nfWeekGridRemounts?:number}).__nfWeekGridRemounts=0;
    new MutationObserver(()=>{
      if(!document.querySelector(".weekly-day-grid"))
        (window as typeof window & {__nfWeekGridRemounts?:number}).__nfWeekGridRemounts!++;
    }).observe(document.querySelector(".family-meals-screen")!,{subtree:true,childList:true});
    document.body.dataset.nfGridKey=key;
  });
  let planRequests=0;
  page.on("request",r=>{if(r.url().includes("/api/families/")&&r.url().includes("/meal-plan?"))planRequests++;});
  const dayButtons=page.locator(".nf-week-day-picker button");
  await expect(dayButtons).toHaveCount(7);
  await dayButtons.nth(1).click();
  await expect(dayButtons.nth(1)).toHaveAttribute("aria-pressed","true");
  await dayButtons.nth(3).click();
  await expect(dayButtons.nth(3)).toHaveAttribute("aria-pressed","true");
  await page.getByRole("button",{name:/Prato sintético QA/}).first().click();
  await expect(page.getByRole("dialog")).toHaveCount(1);
  await page.getByRole("dialog").getByRole("button",{name:"Fechar detalhe"}).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(grid).toBeVisible();
  expect(planRequests).toBe(0);
  expect(await page.evaluate(()=>(window as typeof window & {__nfWeekGridRemounts?:number}).__nfWeekGridRemounts)).toBe(0);
});

test("recipe catalogue stays mounted when closing and reopening a detail",async ({page,request})=>{
  const fixture=await seed(request);
  await openFamily(page,fixture.family.id,"/#/house?tab=recipes");
  const grid=page.locator(".nf-recipe-grid");
  const recipe=page.getByRole("button",{name:/Prato sintético QA/}).first();
  await expect(recipe).toBeVisible();
  let requests=0;
  page.on("request",r=>{if(r.url().includes("/api/families/")&&r.url().includes("/recipes?"))requests++;});
  await recipe.click();
  await expect(page.getByRole("dialog")).toHaveCount(1);
  await expect(grid).toBeAttached();
  await page.getByRole("dialog").getByRole("button",{name:"Fechar detalhe"}).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(recipe).toBeVisible();
  await recipe.click();
  await expect(page.getByRole("dialog")).toHaveCount(1);
  await page.getByRole("dialog").getByRole("button",{name:"Fechar detalhe"}).click();
  await expect(grid).toBeVisible();
  expect(requests).toBe(0);
});

test("meal edit cancel leaves weekly calendar and data untouched without a refetch",async ({page,request})=>{
  const fixture=await seed(request);
  await openFamily(page,fixture.family.id,`/#/meals?date=${DATE}&mode=week`);
  const slot=page.getByRole("button",{name:/Prato sintético QA/}).first();
  await slot.click();
  const dialog=page.getByRole("dialog");
  await expect(dialog).toHaveCount(1);
  let refetches=0;
  page.on("request",r=>{
    if(r.url().includes(`/api/families/${fixture.family.id}/meal-plan?`) && r.method()==="GET")refetches++;
  });
  await dialog.getByRole("button",{name:"Alterar",exact:true}).click();
  await expect(dialog).toHaveCount(1);
  await expect(dialog.locator("form.meal-plan-form")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(page.locator(".weekly-day-grid")).toBeVisible();
  expect(refetches).toBe(0);
});

test("weekly map: editing a saved or empty meal never stacks two side drawers",async ({page,request})=>{
  const fixture=await seed(request);
  await page.setViewportSize({width:1440,height:900});
  await openFamily(page,fixture.family.id,`/#/meals?date=${DATE}&mode=week`);
  const saved=page.getByRole("button",{name:/Prato sintético QA/}).first();
  await saved.click();
  const dialog=page.getByRole("dialog");
  await expect(dialog).toHaveCount(1);
  await dialog.getByRole("button",{name:"Alterar",exact:true}).click();
  await expect(dialog).toHaveCount(1);
  await expect(page.locator("form.meal-plan-form")).toHaveCount(1);
  await expect(page).not.toHaveURL(/meal=dinner/);
  await dialog.getByRole("button",{name:"Cancelar",exact:true}).first().click();
  await expect(dialog).toHaveCount(0);
  await expect(page.locator(".weekly-day-grid")).toBeVisible();

  const empty=page.locator("button.weekly-grid-meal.is-empty").first();
  await expect(empty).toBeVisible();
  await empty.click();
  await expect(dialog).toHaveCount(1);
  await expect(page.locator("form.meal-plan-form")).toHaveCount(1);
  await dialog.getByRole("button",{name:"Cancelar",exact:true}).first().click();
  await expect(dialog).toHaveCount(0);
  await expect(page.locator(".weekly-day-grid")).toBeVisible();
});

test("family taste ratings persist per person independently of nutrition and can be cleared",async ({request})=>{
  const fixture=await seed(request);
  const familyId=fixture.family.id;
  const recipeId=fixture.recipe.id;
  const other=await postJson<{id:string}>(request,`/families/${familyId}/persons`,{
    first_name:"Segundo membro QA",last_name:null,birth_date:null,
    preferred_locale:"pt-PT",timezone:"Europe/Lisbon",meal_discovery:null,
  });
  const base=`/families/${familyId}/recipes/${recipeId}/preferences`;
  const first=await request.put(`${API}${base}/${fixture.person.id}`,{data:{rating:5}});
  expect(first.ok()).toBeTruthy();
  const second=await request.put(`${API}${base}/${other.id}`,{data:{rating:1}});
  expect(second.ok()).toBeTruthy();
  const summary=await getJson<{rating_count:number;average_rating:string|null;ratings:{person_id:string;rating:number}[]}>(request,base);
  expect(summary.rating_count).toBe(2);
  expect(Number(summary.average_rating)).toBe(3);
  expect(summary.ratings.find(x=>x.person_id===fixture.person.id)?.rating).toBe(5);
  expect(summary.ratings.find(x=>x.person_id===other.id)?.rating).toBe(1);
  const clear=await request.delete(`${API}${base}/${other.id}`);
  expect(clear.ok()).toBeTruthy();
  const persisted=await getJson<{rating_count:number;average_rating:string|null;ratings:{person_id:string;rating:number}[]}>(request,base);
  expect(persisted.rating_count).toBe(1);
  expect(Number(persisted.average_rating)).toBe(5);
  expect(persisted.ratings[0]?.person_id).toBe(fixture.person.id);
  const recipe=await getJson<{name:string;ingredients:unknown[]}>(request,`/families/${familyId}/recipes/${recipeId}`);
  expect(recipe.name).toBe("Prato sintético QA");
  expect(recipe.ingredients.length).toBe(1);
});

test("substitution review keeps its recipe list behind one contextual drawer",async ({page,request})=>{
  const fixture=await seed(request);
  await page.setViewportSize({width:390,height:844});
  await openFamily(page,fixture.family.id,"/#/house?tab=substitutions");
  const recipes=page.getByRole("navigation",{name:"Receitas"});
  const item=recipes.getByRole("button",{name:/Prato sintético QA/});
  await expect(item).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await item.click();
  const drawer=page.getByRole("dialog");
  await expect(drawer).toHaveCount(1);
  await expect(drawer.getByRole("heading",{name:"Prato sintético QA"})).toBeVisible();
  await expect(drawer.getByText("Adequação FODMAP ainda não avaliada por porção")).toBeVisible();
  await expect(recipes).toBeAttached();
  await drawer.getByRole("button",{name:"Fechar detalhe"}).click();
  await expect(drawer).toHaveCount(0);
  await expect(item).toBeVisible();
  await page.getByRole("button",{name:"FODMAP · fontes e dados"}).click();
  await expect(page.getByRole("heading",{name:"Monash University"})).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("person meal shortcut selects meal type but requires explicit recipe and preserves person drawer",async ({page,request})=>{
  const fixture=await seed(request);
  const dashboard=await getJson<{dashboard_date:string}>(request,`/families/${fixture.family.id}/dashboard`);
  await postJson(request,`/families/${fixture.family.id}/meal-plan`,{
    date:dashboard.dashboard_date,meal_type:"dinner",local_time:"20:00",
    recipe_id:fixture.recipe.id,participants:[{person_id:fixture.person.id,quantity:"1",unit:"serving"}],
    location:null,notes:null,
  });
  await page.setViewportSize({width:390,height:844});
  await openFamily(page,fixture.family.id,"/#/people");
  const bootstrap=page.waitForRequest(r=>r.url().includes(`/persons/${fixture.person.id}/planning-bootstrap`));
  await page.getByRole("button",{name:/Pessoa QA/}).first().click();
  const nutritionRequest=await bootstrap;
  expect(new URL(nutritionRequest.url()).searchParams.get("scheduled_at")?.startsWith(dashboard.dashboard_date+"T12:00:00")).toBe(true);
  const person=page.getByRole("dialog");
  await expect(person).toHaveCount(1);
  await person.getByRole("button",{name:"Avaliar porção no plano"}).click();
  await expect(person.getByRole("heading",{name:"Nutrição"})).toBeVisible();
  await expect(person.getByText("Refeição selecionada para avaliação: Prato sintético QA")).toBeVisible();
  await expect(person.locator(".plan-fit-controls select").first()).toHaveValue("dinner");
  await expect(person.locator(".plan-fit-controls__recipe select")).toHaveValue("");
  await expect(person.getByRole("button",{name:"Avaliar",exact:true})).toBeDisabled();
  await person.getByRole("button",{name:"Limpar seleção"}).click();
  await expect(person.getByText("Refeição selecionada para avaliação: Prato sintético QA")).toHaveCount(0);
  await expect(person).toHaveCount(1);
});

test("nutrition: late fit response cannot overwrite a changed portion",async ({page,request})=>{
  const fixture=await seed(request);
  // A deliberately synthetic composition enables the evaluator without writing
  // nutritional values or clinical rules to the isolated database.
  await page.route(`**/api/families/${fixture.family.id}/recipes*`,async route=>{
    const response=await route.fetch();
    const recipes=await response.json() as {id:string;latest_composition:unknown;serving_count:string|null}[];
    await route.fulfill({response,json:recipes.map(recipe=>recipe.id===fixture.recipe.id
      ? {...recipe,latest_composition:{
        id:"synthetic-composition-qa",reference_quantity:"2",
        reference_unit:"serving",energy_kcal:"250",
        energy_per_serving_kcal:"125",composition_version:"qa",
        calculation_version:"qa",evidence:"synthetic_development",
        computed_at:"2026-11-20T00:00:00Z",nutrients:[],
      }} : recipe)});
  });
  let releaseResponse:(()=>void)|undefined;
  await page.route(`**/api/persons/${fixture.person.id}/meal-plan-fit`,async route=>{
    await new Promise<void>(resolve=>{releaseResponse=resolve;});
    const payload=route.request().postDataJSON() as {planning_date:string;meal_type:string;candidate:{quantity:string}};
    await route.fulfill({status:200,json:{
      person_id:fixture.person.id,planning_date:payload.planning_date,meal_type:payload.meal_type,
      daily_nutrition_state_id:null,eligible:true,status:"pass",fit_score:"1",
      candidate:{key:"synthetic-qa",name:"Prato sintético QA",kind:"recipe",quantity:payload.candidate.quantity,
        quantity_unit:"serving",nutrition:{energy_kcal:"250",nutrients:{}}},
      active_plans:[],nutrition_plan_authority:{state:"no_active_plan",active_plans:[],
        plan_rule_ids:[],plan_guideline_ids:[],unknown_evidence:[],explanation:[]},
      conflicts:[],safety_issues:[],rule_results:[],guideline_results:[],explanation:[],
    }});
  });
  await openFamily(page,fixture.family.id,"/#/people");
  await page.getByRole("button",{name:/Pessoa QA/}).first().click();
  const person=page.getByRole("dialog");
  await person.getByRole("button",{name:"Nutrição"}).click();
  const evaluator=person.locator(".plan-fit-panel");
  await expect(evaluator.locator(".plan-fit-controls__recipe select")).toHaveValue(fixture.recipe.id);
  const portion=evaluator.locator(".plan-fit-quantity input");
  await portion.fill("1");
  await evaluator.getByRole("button",{name:"Avaliar",exact:true}).click();
  await expect.poll(()=>releaseResponse!==undefined).toBe(true);
  await portion.fill("2");
  const delivered=page.waitForResponse(response=>response.url().endsWith(`/persons/${fixture.person.id}/meal-plan-fit`) && response.request().method()==="POST");
  releaseResponse?.();
  await delivered;
  await expect(evaluator.locator(".plan-fit-result")).toHaveCount(0);
  await expect(portion).toHaveValue("2");
  await expect(evaluator.getByRole("button",{name:"Avaliar",exact:true})).toBeEnabled();
});

test("catalogue and person details open once over their parent list",async ({page,request})=>{
  const fixture=await seed(request);
  await page.setViewportSize({width:1280,height:860});
  await openFamily(page,fixture.family.id,"/#/house?tab=ingredients");
  await page.getByRole("button",{name:/Novo ingrediente/}).click();
  await expect(page.getByRole("dialog")).toHaveCount(1);
  await expect(page.locator(".ingredient-catalogue .ingredient-toolbar")).toHaveCount(1);
  await page.getByRole("dialog").getByRole("button",{name:"Fechar detalhe"}).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator(".ingredient-toolbar")).toBeVisible();

  await page.goto("/#/house?tab=recipes");
  await page.getByRole("button",{name:/Prato sintético QA/}).first().click();
  await expect(page.getByRole("dialog")).toHaveCount(1);
  await expect(page.locator(".recipe-catalogue .nf-recipe-grid")).toHaveCount(1);
  await page.getByRole("dialog").getByRole("button",{name:"Fechar detalhe"}).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator(".nf-recipe-grid")).toBeVisible();

  await page.goto("/#/people");
  await page.getByRole("button",{name:/Pessoa QA/}).first().click();
  await expect(page.getByRole("dialog")).toHaveCount(1);
  await expect(page.locator(".people-list")).toHaveCount(1);
  await page.getByRole("dialog").getByRole("button",{name:"Fechar detalhe"}).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator(".people-list")).toBeVisible();
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

test("weekly mobile route keeps the requested day selected without a meal drawer",async ({page,request})=>{
  const fixture=await seed(request);
  await page.setViewportSize({width:390,height:844});
  await openFamily(page,fixture.family.id,`/#/meals?date=${DATE}&mode=week`);
  const days=page.locator(".nf-week-day-picker button");
  await expect(days).toHaveCount(7);
  await expect(days.nth(3)).toHaveAttribute("aria-pressed","true");
  await expect(page.getByRole("button",{name:/Prato sintético QA/}).first()).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("narrow viewport: weekly drawer reflows at 320 CSS px without horizontal scrolling", async ({page,request})=>{
  const fixture=await seed(request);
  await page.setViewportSize({width:320,height:640});
  await openFamily(page,fixture.family.id,`/#/meals?date=${DATE}&meal=dinner&mode=week`);
  const drawer=page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  await expect(drawer).toContainText("Prato sintético QA");
  const bounds=await drawer.evaluate(element=>element.getBoundingClientRect());
  expect(bounds.left).toBeGreaterThanOrEqual(-1);
  expect(bounds.right).toBeLessThanOrEqual(321);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(321);
  const close=drawer.getByRole("button",{name:"Fechar detalhe"});
  await expect(close).toBeVisible();
  await close.click();
  await expect(drawer).toHaveCount(0);
});

test("accessible drawer: labelled dialog locks scroll, restores page and survives repeated keyboard cycles",async ({page,request})=>{
  const fixture=await seed(request);
  await page.emulateMedia({reducedMotion:"reduce"});
  await page.setViewportSize({width:390,height:844});
  await openFamily(page,fixture.family.id,`/#/meals?date=${DATE}&mode=week`);
  const slot=page.getByRole("button",{name:/Prato sintético QA/}).first();
  await expect(slot).toBeVisible();
  for(let cycle=0;cycle<3;cycle++){
    await slot.focus();
    await slot.click();
    const drawer=page.getByRole("dialog");
    await expect(drawer).toBeVisible();
    const accessible=await drawer.evaluate(element=>{
      const labelledBy=element.getAttribute("aria-labelledby");
      const heading=labelledBy?document.getElementById(labelledBy):null;
      return {modal:element.getAttribute("aria-modal"),labelled:!!heading?.textContent?.trim(),
        overflow:document.body.style.overflow,backgroundInert:document.getElementById("root")?.inert};
    });
    expect(accessible).toEqual({modal:"true",labelled:true,overflow:"hidden",backgroundInert:true});
    await expect(drawer.getByRole("button",{name:"Fechar detalhe"})).toBeFocused();
    for(let i=0;i<8;i++){
      await page.keyboard.press(i%2===0?"Tab":"Shift+Tab");
      expect(await page.evaluate(()=>Boolean(document.activeElement?.closest('[role="dialog"]')))).toBe(true);
    }
    await page.keyboard.press("Escape");
    await expect(drawer).toHaveCount(0);
    await expect(page.locator("#root")).not.toHaveAttribute("inert","");
    expect(await page.evaluate(()=>document.body.style.overflow)).not.toBe("hidden");
    await expect(slot).toBeFocused();
  }
});

test("drawer keyboard navigation skips hidden and fieldset-disabled controls",async ({page,request})=>{
  const fixture=await seed(request);
  await page.emulateMedia({reducedMotion:"reduce"});
  await openFamily(page,fixture.family.id,`/#/meals?date=${DATE}&meal=dinner&mode=week`);
  const drawer=page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  const close=drawer.getByRole("button",{name:"Fechar detalhe"});
  await expect(close).toBeFocused();
  // Inject only test controls into the temporary browser DOM; no backend writes.
  await drawer.evaluate(element=>{
    const hidden=document.createElement("button");
    hidden.textContent="Hidden focus trap QA";
    hidden.id="nf-hidden-focus-qa";
    hidden.style.visibility="hidden";
    element.appendChild(hidden);
    const fieldset=document.createElement("fieldset");
    fieldset.disabled=true;
    const disabled=document.createElement("button");
    disabled.id="nf-disabled-focus-qa";
    disabled.textContent="Disabled focus trap QA";
    fieldset.appendChild(disabled);
    element.appendChild(fieldset);
  });
  await page.keyboard.press("Shift+Tab");
  await expect(close).not.toBeFocused();
  const target=await page.evaluate(()=>({
    inDialog:Boolean(document.activeElement?.closest('[role="dialog"]')),
    id:(document.activeElement as HTMLElement|null)?.id,
  }));
  expect(target.inDialog).toBe(true);
  expect(target.id).not.toBe("nf-hidden-focus-qa");
  expect(target.id).not.toBe("nf-disabled-focus-qa");
  await page.keyboard.press("Escape");
  await expect(drawer).toHaveCount(0);
});

test("accessible drawer reclaims programmatic focus outside the modal and restores it on close",async ({page,request})=>{
  const fixture=await seed(request);
  await page.emulateMedia({reducedMotion:"reduce"});
  await openFamily(page,fixture.family.id,`/#/meals?date=${DATE}&mode=week`);
  const slot=page.getByRole("button",{name:/Prato sintético QA/}).first();
  await slot.click();
  const drawer=page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  const close=drawer.getByRole("button",{name:"Fechar detalhe"});
  await expect(close).toBeFocused();
  // Simulate an unrelated script attempting to focus an element outside the modal.
  // The target is outside #root so inert alone cannot make this check pass.
  const result=await page.evaluate(()=>{
    const outside=document.createElement("button");
    outside.id="outside-dialog-focus-qa";
    outside.textContent="External test focus target";
    document.body.appendChild(outside);
    outside.focus();
    const inModal=Boolean(document.activeElement?.closest('[role="dialog"]'));
    outside.remove();
    return inModal;
  });
  expect(result).toBe(true);
  await expect(close).toBeFocused();
  await close.click();
  await expect(drawer).toHaveCount(0);
  await expect(slot).toBeFocused();
  expect(await page.evaluate(()=>document.body.style.overflow)).not.toBe("hidden");
});

test("shopping: edit manual item in one drawer without losing the list or cancelled data",async ({page,request})=>{
  const fixture=await seed(request);
  await page.setViewportSize({width:390,height:844});
  await openFamily(page,fixture.family.id,"/#/shopping");
  await expect(page.getByRole("heading",{name:"Lista de compras"})).toBeVisible();
  const manual=page.locator("details.nf-manual-shopping");
  await manual.locator("summary").click();
  await manual.getByRole("textbox",{name:"Item"}).fill("Produto fictício QA");
  await manual.getByRole("button",{name:"Adicionar",exact:true}).click();
  const edit=page.getByRole("button",{name:"Editar: Produto fictício QA"});
  await expect(edit).toBeVisible();
  await edit.click();
  const drawer=page.getByRole("dialog");
  await expect(drawer).toHaveCount(1);
  await expect(page.locator(".shopping-item")).toHaveCount(1);
  const form=drawer.locator("form.shopping-edit-card");
  await form.getByRole("textbox",{name:"Item"}).fill("Produto alterado QA");
  await expect(form.getByText("Alterações por guardar")).toBeVisible();
  page.once("dialog",prompt=>prompt.dismiss());
  await form.getByRole("button",{name:"Cancelar"}).click();
  await expect(drawer).toHaveCount(1);
  await expect(form.getByRole("textbox",{name:"Item"})).toHaveValue("Produto alterado QA");
  page.once("dialog",prompt=>prompt.accept());
  await form.getByRole("button",{name:"Cancelar"}).click();
  await expect(drawer).toHaveCount(0);
  await expect(edit).toBeVisible();
  await expect(page.getByText("Produto fictício QA", {exact:true})).toBeVisible();

  await edit.click();
  await expect(drawer).toHaveCount(1);
  await form.getByRole("textbox",{name:"Item"}).fill("Produto confirmado QA");
  await form.getByRole("button",{name:"Guardar"}).click();
  await expect(drawer).toHaveCount(0);
  await expect(page.getByText("Produto confirmado QA",{exact:true})).toBeVisible();
});

test("pantry: create stock in a drawer without replacing list and protect unsaved changes",async ({page,request})=>{
  const fixture=await seed(request);
  await page.setViewportSize({width:390,height:844});
  await openFamily(page,fixture.family.id,"/#/house?tab=pantry");
  const add=page.getByRole("button",{name:"Adicionar stock"}).first();
  await expect(add).toBeVisible();
  await add.click();
  const dialog=page.getByRole("dialog");
  await expect(dialog).toHaveCount(1);
  await expect(page.locator(".pantry-list")).toBeAttached();
  const form=dialog.locator("form.pantry-editor");
  await expect(form).toBeVisible();
  await form.getByLabel("Quantidade").fill("3");
  await expect(form.getByText("Alterações por guardar")).toBeVisible();
  page.once("dialog",prompt=>prompt.dismiss());
  await form.getByRole("button",{name:"Cancelar"}).click();
  await expect(dialog).toHaveCount(1);
  await expect(form.getByLabel("Quantidade")).toHaveValue("3");
  page.once("dialog",prompt=>prompt.accept());
  await form.getByRole("button",{name:"Cancelar"}).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.locator(".pantry-list")).toBeAttached();
  await expect(add).toBeVisible();
  await expect(page.getByText("Ainda não há stock registado.")).toBeVisible();
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

test("ingredient editor reflows at 320 and 390 CSS pixels in light and dark themes",async ({page,request})=>{
  const fixture=await seed(request);
  await page.emulateMedia({reducedMotion:"reduce"});
  for(const width of [320,390]){
    await page.setViewportSize({width,height:800});
    for(const theme of ["light","dark"]){
      await openFamily(page,fixture.family.id,"/#/house?tab=ingredients");
      await page.evaluate(value=>window.localStorage.setItem("nutriflow-appearance",value),theme);
      await page.reload();
      await expect(page.locator("html")).toHaveAttribute("data-theme",theme);
      await page.getByRole("button",{name:/Novo ingrediente/}).click();
      const name=page.getByLabel("Nome",{exact:true});
      await expect(name).toBeVisible();
      await name.fill(`Ingrediente responsivo QA ${width} ${theme}`);
      await expect(page.getByText("Alterações por guardar")).toBeVisible();
      const geometry=await page.evaluate(()=>{
        const field=document.querySelector<HTMLInputElement>('input[name="name"]');
        const rect=field?.getBoundingClientRect();
        return {
          viewport:window.innerWidth,
          documentWidth:document.documentElement.scrollWidth,
          fieldLeft:rect?.left??null,
          fieldRight:rect?.right??null,
        };
      });
      expect(geometry.documentWidth,`Page overflow at ${width}px / ${theme}`).toBeLessThanOrEqual(geometry.viewport+1);
      if(geometry.fieldLeft!==null&&geometry.fieldRight!==null){
        expect(geometry.fieldLeft).toBeGreaterThanOrEqual(-1);
        expect(geometry.fieldRight).toBeLessThanOrEqual(geometry.viewport+1);
      }
      await expect(page.getByRole("button",{name:"Guardar",exact:true})).toBeVisible();
    }
  }
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

test("health condition form: mobile reflow and cancelled draft never persists",async ({page,request})=>{
  const fixture=await seed(request);
  await page.emulateMedia({reducedMotion:"reduce"});
  for(const {width,theme} of [{width:320,theme:"light"},{width:390,theme:"dark"}]){
    await page.setViewportSize({width,height:800});
    await openFamily(page,fixture.family.id,`/#/people?person=${fixture.person.id}`);
    await page.evaluate(value=>window.localStorage.setItem("nutriflow-appearance",value),theme);
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme",theme);
    await page.getByRole("button",{name:"Saúde",exact:true}).click();
    await page.getByRole("button",{name:"Adicionar condição"}).click();
    const form=page.locator("form.nf-condition-form");
    await expect(form).toBeVisible();
    await form.getByLabel("Nome da condição").fill("Condição fictícia de teste");
    await form.getByLabel(/Código estável/).fill("qa-test-draft");
    await expect(form.getByText("Alterações por guardar")).toBeVisible();
    const geometry=await form.evaluate(element=>{
      const rect=element.getBoundingClientRect();
      return {viewport:innerWidth,scrollWidth:document.documentElement.scrollWidth,
        left:rect.left,right:rect.right,client:element.clientWidth,scroll:element.scrollWidth};
    });
    expect(geometry.scrollWidth,`Page overflow at ${width}px / ${theme}`).toBeLessThanOrEqual(geometry.viewport+1);
    expect(geometry.left).toBeGreaterThanOrEqual(-1);
    expect(geometry.right).toBeLessThanOrEqual(geometry.viewport+1);
    expect(geometry.scroll,`Form overflow at ${width}px / ${theme}`).toBeLessThanOrEqual(geometry.client+2);
    page.once("dialog",dialog=>dialog.dismiss());
    await form.getByRole("button",{name:"Cancelar"}).click();
    await expect(form.getByLabel("Nome da condição")).toHaveValue("Condição fictícia de teste");
    page.once("dialog",dialog=>dialog.accept());
    await form.getByRole("button",{name:"Cancelar"}).click();
    await expect(form).toHaveCount(0);
    await expect(page.getByText("Sem condições registadas.")).toBeVisible();
  }
});

test("person profile editor: narrow responsive layout and unsaved draft guard",async ({page,request})=>{
  const fixture=await seed(request);
  await page.emulateMedia({reducedMotion:"reduce"});
  for(const width of [320,390]){
    await page.setViewportSize({width,height:800});
    await openFamily(page,fixture.family.id,`/#/people?person=${fixture.person.id}`);
    await page.getByRole("button",{name:"Perfil",exact:true}).click();
    await page.getByRole("button",{name:"Editar perfil"}).click();
    const form=page.locator("form.person-profile-form");
    await expect(form).toBeVisible();
    await expect(form.getByLabel("Nome",{exact:true})).toHaveValue("Pessoa QA");
    await form.getByLabel("Nome",{exact:true}).fill(`Pessoa QA ${width}`);
    await expect(form.getByText("Alterações por guardar")).toBeVisible();
    const metrics=await page.evaluate(()=>{
      const form=document.querySelector("form.person-profile-form");
      const rect=form?.getBoundingClientRect();
      return {viewport:innerWidth,scrollWidth:document.documentElement.scrollWidth,
        left:rect?.left??0,right:rect?.right??0};
    });
    expect(metrics.scrollWidth,`Page overflow at ${width}px`).toBeLessThanOrEqual(metrics.viewport+1);
    expect(metrics.left).toBeGreaterThanOrEqual(-1);
    expect(metrics.right).toBeLessThanOrEqual(metrics.viewport+1);
    page.once("dialog",dialog=>dialog.dismiss());
    await form.getByRole("button",{name:"Cancelar"}).click();
    await expect(form.getByText("Alterações por guardar")).toBeVisible();
    page.once("dialog",dialog=>dialog.accept());
    await form.getByRole("button",{name:"Cancelar"}).click();
    await expect(form).toHaveCount(0);
    const persisted=await getJson<{id:string;first_name:string}[]>(request,`/families/${fixture.family.id}/persons`);
    expect(persisted.find(person=>person.id===fixture.person.id)?.first_name).toBe("Pessoa QA");
  }
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

test("API: concurrent daily nutrition refreshes create a single state without a uniqueness conflict",async ({request})=>{
  const family=await postJson<{id:string}>(request,"/families",{
    name:"Família concorrência QA",
    timezone:"Europe/Lisbon",
    meal_discovery_sources:["shared_recipes"],
    delivery_address:null,restaurant_area:null,
  });
  const person=await postJson<{id:string}>(request,`/families/${family.id}/persons`,{
    first_name:"Concorrência QA",last_name:null,birth_date:null,
    preferred_locale:"pt-PT",timezone:"Europe/Lisbon",meal_discovery:null,
  });
  const requests=Array.from({length:10},()=>request.get(`${API}/persons/${person.id}/planning-bootstrap`,{
    params:{scheduled_at:"2026-11-19T20:00:00+00:00",ensure_state:"true"},
  }));
  const responses=await Promise.all(requests);
  for(const response of responses){
    expect(response.status(), `Concurrent state refresh returned HTTP ${response.status()}: ${await response.text()}`).toBe(200);
  }
  const states=await Promise.all(responses.map(async response=>
    (await response.json() as {daily_nutrition_state:{id:string}|null}).daily_nutrition_state?.id
  ));
  expect(states.every(id=>typeof id==="string")).toBe(true);
  expect(new Set(states).size).toBe(1);
});

test("adaptation: accepted recipe edit updates only selected meal and shopping after confirmation",async ({request})=>{
  const fixture=await seed(request);
  const familyId=fixture.family.id;
  const basePath=`/families/${familyId}`;
  const replacement=await postJson<{id:string}>(request,`${basePath}/ingredients`,{
    name:"Batata sintética QA",brand:null,description:null,composition:null,
  });
  const baseRecipe=await getJson<{
    id:string;serving_count:string|null;yield_quantity:string|null;yield_unit:string|null;
    ingredients:{id:string,food_item_id:string,quantity:string,unit:string,preparation:string|null}[]
  }>(request,`${basePath}/recipes/${fixture.recipe.id}`);
  expect(baseRecipe.ingredients).toHaveLength(1);
  const original=baseRecipe.ingredients[0]!;
  const edit=await postJson<{id:string,recipe_id:string,confirmation_mode:string}>(request,`${basePath}/recipe-variants/recipe-edit`,{
    base_recipe_id:fixture.recipe.id,
    name:"Prato sintético adaptado QA",
    serving_count:null,
    operations:[{
      recipe_ingredient_id:original.id,
      replacement_food_item_id:replacement.id,
      replacement_name:"Batata sintética QA",
      quantity:String(original.quantity),
      unit:original.unit,
      preparation:original.preparation??"",
    }],
  });
  expect(edit.confirmation_mode).toBe("recipe_edit");
  expect(edit.recipe_id).not.toBe(fixture.recipe.id);
  const revised=await getJson<typeof baseRecipe>(request,`${basePath}/recipes/${edit.recipe_id}`);
  expect(revised.serving_count).toBe(baseRecipe.serving_count);
  expect(revised.yield_quantity).toBe(baseRecipe.yield_quantity);
  expect(revised.yield_unit).toBe(baseRecipe.yield_unit);
  expect(revised.ingredients).toEqual([
    expect.objectContaining({
      food_item_id:replacement.id,
      quantity:original.quantity,
      unit:original.unit,
      preparation:original.preparation,
    }),
  ]);
  // Merely reviewing / saving a variant must not rewrite the existing meal or shopping.
  const originalPlan=await getJson<{days:{date:string,slots:{meal_type:string,meals:{id:string,recipe_id:string}[]}[]}[]}>(request,
    `${basePath}/meal-plan?start_date=2026-11-16&days=7`);
  const beforeEntry=originalPlan.days.find(day=>day.date===DATE)?.slots.find(slot=>slot.meal_type==="dinner")?.meals[0];
  expect(beforeEntry?.recipe_id).toBe(fixture.recipe.id);
  const beforeShopping=await postJson<{
    requirements:{food_item_id:string,required_quantity:string}[];
    planning_issues:string[];
  }>(request,`${basePath}/shopping-list/refresh`,{start_date:"2026-11-16",days:7});
  expect(beforeShopping.requirements.some(row=>row.food_item_id===fixture.ingredient.id)).toBe(true);
  expect(beforeShopping.requirements.some(row=>row.food_item_id===replacement.id)).toBe(false);

  const changed=await request.patch(`${API}${basePath}/meal-plan/${fixture.meal.id}`,{
    data:{
      expected_updated_at:(await getJson<{
        days:{date:string,slots:{meal_type:string,meals:{id:string,updated_at:string}[]}[]}[]
      }>(request,`${basePath}/meal-plan?start_date=2026-11-16&days=7`))
        .days.find(day=>day.date===DATE)?.slots.find(slot=>slot.meal_type==="dinner")?.meals[0]?.updated_at,
      recipe_id:edit.recipe_id,
      participants:[{person_id:fixture.person.id,quantity:"1",unit:"serving"}],
    },
  });
  expect(changed.ok(),`Recipe edit cannot be confirmed: HTTP ${changed.status()} ${await changed.text()}`).toBe(true);
  const confirmed=await changed.json() as {recipe_id:string,recipe_name:string};
  expect(confirmed.recipe_id).toBe(edit.recipe_id);
  const afterShopping=await postJson<typeof beforeShopping>(request,`${basePath}/shopping-list/refresh`,{
    start_date:"2026-11-16",days:7,
  });
  expect(afterShopping.requirements.some(row=>row.food_item_id===replacement.id)).toBe(true);
  expect(afterShopping.requirements.some(row=>row.food_item_id===fixture.ingredient.id)).toBe(false);
  const stillOriginal=await getJson<typeof baseRecipe>(request,`${basePath}/recipes/${fixture.recipe.id}`);
  expect(stillOriginal.ingredients[0]?.food_item_id).toBe(fixture.ingredient.id);
});

test("adaptation: a family-declared replacement stays uncertified and does not change shopping until confirmation",async ({request})=>{
  const fixture=await seed(request);
  const base=`/families/${fixture.family.id}`;
  const originalRecipe=await getJson<{
    id:string;serving_count:string|null;yield_quantity:string|null;yield_unit:string|null;
    ingredients:{id:string,food_item_id:string,quantity:string,unit:string,preparation:string|null}[]
  }>(request,`${base}/recipes/${fixture.recipe.id}`);
  const line=originalRecipe.ingredients[0]!;
  const draft=await postJson<{id:string,recipe_id:string,confirmation_mode:string}>(request,`${base}/recipe-variants/recipe-edit`,{
    base_recipe_id:fixture.recipe.id,
    name:"Prato com ingrediente declarado pela família QA",
    serving_count:null,
    operations:[{
      recipe_ingredient_id:line.id,replacement_food_item_id:null,
      replacement_name:"Alternativa descritiva sem rótulo QA",
      quantity:line.quantity,unit:line.unit,preparation:"",
    }],
  });
  expect(draft.confirmation_mode).toBe("recipe_edit");
  const revised=await getJson<{
    source:string;serving_count:string|null;yield_quantity:string|null;yield_unit:string|null;
    ingredients:{food_item_name:string,food_item_id:string,quantity:string,unit:string,preparation:string|null,has_nutrition:boolean,has_energy:boolean}[];
    latest_composition:{energy_kcal:string|null,energy_per_serving_kcal:string|null}|null;
  }>(request,`${base}/recipes/${draft.recipe_id}`);
  expect(revised.source).toBe("family_adaptation");
  expect(revised.serving_count).toBe(originalRecipe.serving_count);
  expect(revised.yield_quantity).toBe(originalRecipe.yield_quantity);
  expect(revised.yield_unit).toBe(originalRecipe.yield_unit);
  expect(revised.ingredients).toEqual([expect.objectContaining({
    food_item_name:"Alternativa descritiva sem rótulo QA",
    quantity:line.quantity,unit:line.unit,preparation:null,
    has_nutrition:false,has_energy:false,
  })]);
  expect(revised.latest_composition?.energy_kcal??null).toBeNull();
  expect(revised.latest_composition?.energy_per_serving_kcal??null).toBeNull();

  const preview=await postJson<{requirements:{food_item_id:string}[]}>(request,`${base}/shopping-list/refresh`,{
    start_date:"2026-11-16",days:7,
  });
  expect(preview.requirements.some(x=>x.food_item_id===fixture.ingredient.id)).toBe(true);
  expect(preview.requirements.some(x=>x.food_item_id===revised.ingredients[0]?.food_item_id)).toBe(false);

  const result=await request.patch(`${API}${base}/meal-plan/${fixture.meal.id}`,{
    data:{recipe_id:draft.recipe_id,participants:[{
      person_id:fixture.person.id,quantity:"1",unit:"serving",
    }]},
  });
  expect(result.ok(),`Cannot confirm described adaptation: ${result.status()} ${await result.text()}`).toBe(true);
  const after=await postJson<{requirements:{food_item_id:string,food_item_name:string}[]}>(request,`${base}/shopping-list/refresh`,{
    start_date:"2026-11-16",days:7,
  });
  expect(after.requirements.some(x=>x.food_item_id===revised.ingredients[0]?.food_item_id)).toBe(true);
  expect(after.requirements.some(x=>x.food_item_id===fixture.ingredient.id)).toBe(false);
  const original=await getJson<typeof originalRecipe>(request,`${base}/recipes/${fixture.recipe.id}`);
  expect(original.ingredients[0]?.food_item_id).toBe(fixture.ingredient.id);
});

test("adaptation isolation: another meal retains its original recipe and shopping follows removal",async ({request})=>{
  const fixture=await seed(request);
  const base=`/families/${fixture.family.id}`;
  const original=await getJson<{ingredients:{id:string,quantity:string,unit:string}[]}>(request,
    `${base}/recipes/${fixture.recipe.id}`);
  const second=await postJson<{id:string,recipe_id:string}>(request,`${base}/meal-plan`,{
    date:"2026-11-20",meal_type:"lunch",local_time:"13:00",
    recipe_id:fixture.recipe.id,participants:[{
      person_id:fixture.person.id,quantity:"1",unit:"serving",
    }],location:null,notes:null,
  });
  const replacement=await postJson<{id:string}>(request,`${base}/ingredients`,{
    name:"Ingrediente alternativo isolado QA",brand:null,description:null,composition:null,
  });
  const changed=await postJson<{recipe_id:string}>(request,`${base}/recipe-variants/recipe-edit`,{
    base_recipe_id:fixture.recipe.id,name:"Prato alternativo isolado QA",
    serving_count:null,
    operations:[{
      recipe_ingredient_id:original.ingredients[0]!.id,
      replacement_food_item_id:replacement.id,
      replacement_name:"Ingrediente alternativo isolado QA",
      quantity:original.ingredients[0]!.quantity,
      unit:original.ingredients[0]!.unit,preparation:"",
    }],
  });
  const updated=await request.patch(`${API}${base}/meal-plan/${fixture.meal.id}`,{
    data:{recipe_id:changed.recipe_id,participants:[{
      person_id:fixture.person.id,quantity:"1",unit:"serving",
    }]},
  });
  expect(updated.ok(),`Cannot adapt selected meal: ${updated.status()} ${await updated.text()}`).toBe(true);
  const map=await getJson<{days:{date:string,slots:{meal_type:string,meals:{id:string,recipe_id:string}[]}[]}[]}>(request,
    `${base}/meal-plan?start_date=2026-11-16&days=7`);
  expect(map.days.find(day=>day.date===DATE)?.slots.find(slot=>slot.meal_type==="dinner")?.meals[0]?.recipe_id).toBe(changed.recipe_id);
  expect(map.days.find(day=>day.date==="2026-11-20")?.slots.find(slot=>slot.meal_type==="lunch")?.meals[0]?.id).toBe(second.id);
  expect(map.days.find(day=>day.date==="2026-11-20")?.slots.find(slot=>slot.meal_type==="lunch")?.meals[0]?.recipe_id).toBe(fixture.recipe.id);
  const refreshed=await postJson<{requirements:{food_item_id:string}[]}>(request,
    `${base}/shopping-list/refresh`,{start_date:"2026-11-16",days:7});
  expect(refreshed.requirements.some(x=>x.food_item_id===fixture.ingredient.id)).toBe(true);
  expect(refreshed.requirements.some(x=>x.food_item_id===replacement.id)).toBe(true);
  const removed=await request.delete(`${API}${base}/meal-plan/${fixture.meal.id}`);
  expect(removed.status()).toBe(204);
  const afterRemoval=await postJson<typeof refreshed>(request,`${base}/shopping-list/refresh`,{
    start_date:"2026-11-16",days:7,
  });
  expect(afterRemoval.requirements.some(x=>x.food_item_id===fixture.ingredient.id)).toBe(true);
  expect(afterRemoval.requirements.some(x=>x.food_item_id===replacement.id)).toBe(false);
});

test("UI adaptation flow: family recipe edit is explicitly not certified before final confirmation",async ({page,request})=>{
  const fixture=await seed(request);
  const base=`/families/${fixture.family.id}`;
  const replacement=await postJson<{id:string}>(request,`${base}/ingredients`,{
    name:"Legume alternativo QA",brand:null,description:null,composition:null,
  });
  const recipe=await getJson<{ingredients:{id:string,quantity:string,unit:string}[]}>(request,
    `${base}/recipes/${fixture.recipe.id}`);
  const edit=await postJson<{recipe_id:string}>(request,`${base}/recipe-variants/recipe-edit`,{
    base_recipe_id:fixture.recipe.id,name:"Prato editado sem certificação QA",
    serving_count:null,
    operations:[{
      recipe_ingredient_id:recipe.ingredients[0]!.id,
      replacement_food_item_id:replacement.id,
      replacement_name:"Legume alternativo QA",
      quantity:recipe.ingredients[0]!.quantity,unit:recipe.ingredients[0]!.unit,
      preparation:"",
    }],
  });
  await openFamily(page,fixture.family.id,`/#/meals?date=${DATE}&meal=dinner&mode=week`);
  const drawer=page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  await drawer.getByRole("button",{name:"Preparar as trocas"}).click();
  await drawer.getByRole("button",{name:"Rever receita com estas escolhas"}).click();
  await drawer.getByText(/Usar uma adaptação já guardada/).click();
  await drawer.getByRole("button",{name:"Usar e rever esta adaptação"}).click();
  await drawer.getByRole("button",{name:"Seguir para confirmação final"}).click();
  await expect(drawer.getByRole("heading",{name:"Escolha da família · não é validação nutricional"})).toBeVisible();
  await expect(drawer.getByText(/Não certifica a adequação nutricional nem a segurança clínica/)).toBeVisible();
  const before=await getJson<{days:{date:string,slots:{meal_type:string,meals:{recipe_id:string}[]}[]}[]}>(request,
    `${base}/meal-plan?start_date=2026-11-16&days=7`);
  expect(before.days.find(d=>d.date===DATE)?.slots.find(s=>s.meal_type==="dinner")?.meals[0]?.recipe_id).toBe(fixture.recipe.id);
  await drawer.getByRole("button",{name:"Confirmar esta refeição no plano"}).click();
  await expect.poll(async()=>{
    const after=await getJson<typeof before>(request,`${base}/meal-plan?start_date=2026-11-16&days=7`);
    return after.days.find(d=>d.date===DATE)?.slots.find(s=>s.meal_type==="dinner")?.meals[0]?.recipe_id;
  }).toBe(edit.recipe_id);
});

test("drafts: save incomplete substitution, reload, update optimistically and leave meal/shopping unchanged",async ({request})=>{
  const fixture=await seed(request);
  const base=`/families/${fixture.family.id}`;
  const recipe=await getJson<{ingredients:{id:string}[]}>(request,`${base}/recipes/${fixture.recipe.id}`);
  const ingredientId=recipe.ingredients[0]!.id;
  const shoppingBefore=await postJson<{
    requirements:{food_item_id:string,required_quantity:string}[];
  }>(request,`${base}/shopping-list/refresh`,{start_date:"2026-11-16",days:7});
  const snapshot={
    base_recipe_id:fixture.recipe.id,meal_event_id:fixture.meal.id,
    planning_date:DATE,meal_type:"dinner",
    name:"Adaptação incompleta QA",serving_count:"",
    operations:[{recipe_ingredient_id:ingredientId,replacement_food_item_id:null,
      replacement_name:"Alternativa por decidir",quantity:"",unit:"",preparation:""}],
    participants:[{person_id:fixture.person.id,quantity:"",unit:"serving"}],
    decisions:{[ingredientId]:"manual"},
  };
  const saved=await postJson<{id:string,version:number,status:string,snapshot:typeof snapshot}>(
    request,`${base}/meal-adaptation-drafts`,snapshot);
  expect(saved.status).toBe("draft");
  expect(saved.snapshot.operations[0]?.quantity).toBe("");
  expect(saved.snapshot.serving_count).toBe("");
  expect(saved.snapshot.participants[0]?.quantity).toBe("");
  const resumed=await getJson<{id:string,version:number,snapshot:typeof snapshot}[]>(
    request,`${base}/meal-adaptation-drafts?base_recipe_id=${fixture.recipe.id}`);
  expect(resumed.find(item=>item.id===saved.id)?.snapshot).toEqual(saved.snapshot);

  const amended={...snapshot,name:"Adaptação retomada QA",
    operations:[{...snapshot.operations[0],quantity:"150",unit:"g"}]};
  const update=await request.put(`${API}${base}/meal-adaptation-drafts/${saved.id}`,{
    data:{...amended,expected_version:saved.version},
  });
  expect(update.ok(),`Cannot resume draft: ${update.status()} ${await update.text()}`).toBe(true);
  const current=await update.json() as {version:number,snapshot:typeof snapshot};
  expect(current.version).toBe(saved.version+1);
  expect(current.snapshot.operations[0]?.quantity).toBe("150");
  expect(current.snapshot.participants[0]?.quantity).toBe("");
  const stale=await request.put(`${API}${base}/meal-adaptation-drafts/${saved.id}`,{
    data:{...snapshot,expected_version:saved.version},
  });
  expect(stale.status()).toBe(409);
  const plan=await getJson<{days:{date:string,slots:{meal_type:string,meals:{id:string,recipe_id:string}[]}[]}[]}>(
    request,`${base}/meal-plan?start_date=2026-11-16&days=7`);
  expect(plan.days.find(day=>day.date===DATE)?.slots.find(slot=>slot.meal_type==="dinner")?.meals[0]).toEqual(
    expect.objectContaining({id:fixture.meal.id,recipe_id:fixture.recipe.id}));
  const shoppingAfter=await postJson<typeof shoppingBefore>(
    request,`${base}/shopping-list/refresh`,{start_date:"2026-11-16",days:7});
  expect(shoppingAfter.requirements).toEqual(shoppingBefore.requirements);
});

test("UI adaptation draft: save an incomplete recipe and resume after drawer reload",async ({page,request})=>{
  const fixture=await seed(request);
  const familyId=fixture.family.id;
  const replacement=await postJson<{id:string}>(request,`/families/${familyId}/ingredients`,{
    name:"Legume para rascunho QA",brand:null,description:null,composition:null,
  });
  await openFamily(page,familyId,`/#/meals?date=${DATE}&meal=dinner&mode=week`);
  const drawer=page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  await drawer.getByRole("button",{name:"Preparar as trocas"}).click();
  await drawer.getByText("Acrescentar substituição de outro ingrediente").click();
  await drawer.getByLabel("Ingrediente da receita").selectOption({index:1});
  await drawer.getByRole("button",{name:"Adicionar troca manual"}).click();
  await drawer.getByLabel("Trocar por (ingrediente do catálogo)").selectOption(replacement.id);
  await drawer.getByLabel("Quantidade na receita inteira").fill("");
  await drawer.getByRole("button",{name:"Usar esta escolha manual"}).click();
  await drawer.getByRole("button",{name:"Rever receita com estas escolhas"}).click();
  await expect(drawer.getByRole("button",{name:"Guardar para continuar depois"})).toBeVisible();
  await drawer.getByRole("button",{name:"Guardar para continuar depois"}).click();
  await expect(drawer.getByText(/Rascunho guardado com pendências/)).toBeVisible();
  const before=await getJson<{days:{date:string,slots:{meal_type:string,meals:{recipe_id:string}[]}[]}[]}>(
    request,`/families/${familyId}/meal-plan?start_date=2026-11-16&days=7`);
  expect(before.days.find(d=>d.date===DATE)?.slots.find(s=>s.meal_type==="dinner")?.meals[0]?.recipe_id).toBe(fixture.recipe.id);
  await page.reload();
  await expect(drawer).toBeVisible();
  await drawer.getByRole("button",{name:"Preparar as trocas"}).click();
  await drawer.getByRole("button",{name:/Retomar rascunho: /}).click();
  await expect(drawer.getByText(/Rascunho recuperado com os dados em falta preservados/)).toBeVisible();
  await expect(drawer.getByRole("button",{name:"Guardar para continuar depois"})).toBeVisible();
});

test("stale draft: changed source recipe is flagged and shown for review without applying the edit",async ({page,request})=>{
  const fixture=await seed(request);
  const base=`/families/${fixture.family.id}`;
  const recipe=await getJson<{ingredients:{id:string}[]}>(request,`${base}/recipes/${fixture.recipe.id}`);
  const ingredientId=recipe.ingredients[0]!.id;
  const draft=await postJson<{id:string}>(request,`${base}/meal-adaptation-drafts`,{
    base_recipe_id:fixture.recipe.id,meal_event_id:fixture.meal.id,planning_date:DATE,meal_type:"dinner",
    name:"Rascunho sujeito a alteração QA",serving_count:"",
    operations:[{recipe_ingredient_id:ingredientId,replacement_food_item_id:null,
      replacement_name:"Alternativa por decidir",quantity:"",unit:"",preparation:""}],
    participants:[{person_id:fixture.person.id,quantity:"",unit:"serving"}],
    decisions:{[ingredientId]:"manual"},
  });
  const changed=await request.patch(`${API}${base}/recipes/${fixture.recipe.id}`,{
    data:{name:"Prato original revisto QA"},
  });
  expect(changed.ok(),`Cannot update original recipe: ${changed.status()} ${await changed.text()}`).toBe(true);
  const drafts=await getJson<{id:string,base_changed:boolean}[]>(request,
    `${base}/meal-adaptation-drafts?base_recipe_id=${fixture.recipe.id}`);
  expect(drafts.find(row=>row.id===draft.id)?.base_changed).toBe(true);
  await openFamily(page,fixture.family.id,`/#/meals?date=${DATE}&meal=dinner&mode=week`);
  const drawer=page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  await drawer.getByRole("button",{name:"Preparar as trocas"}).click();
  await drawer.getByRole("button",{name:/Retomar rascunho: /}).click();
  await expect(drawer.getByText(/A receita base mudou desde este rascunho/)).toBeVisible();
  const current=await getJson<{days:{date:string,slots:{meal_type:string,meals:{id:string,recipe_id:string}[]}[]}[]}>(
    request,`${base}/meal-plan?start_date=2026-11-16&days=7`);
  expect(current.days.find(day=>day.date===DATE)?.slots.find(slot=>slot.meal_type==="dinner")?.meals[0]).toEqual(
    expect.objectContaining({id:fixture.meal.id,recipe_id:fixture.recipe.id}));
});

test("attendance reuse: copy only people from an earlier dinner and keep source meal unchanged",async ({page,request})=>{
  const fixture=await seed(request);
  const familyId=fixture.family.id;
  const second=await postJson<{id:string}>(request,`/families/${familyId}/persons`,{
    first_name:"Outra pessoa QA",last_name:null,birth_date:null,
    preferred_locale:"pt-PT",timezone:"Europe/Lisbon",meal_discovery:null,
  });
  await openFamily(page,familyId,"/#/meals?date=2026-11-20&meal=dinner&mode=week");
  const drawer=page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  await drawer.getByRole("button",{name:"Escolher receita"}).click();
  const editor=page.getByRole("dialog");
  await expect(editor).toBeVisible();
  await expect(editor.getByRole("heading",{name:"Jantar",exact:true})).toBeVisible();
  const before=await getJson<{days:{date:string,slots:{meal_type:string,meals:{id:string,participants:{person_id:string}[]}[]}[]}[]}>(
    request,`/families/${familyId}/meal-plan?start_date=2026-11-16&days=7`);
  expect(before.days.find(d=>d.date==="2026-11-20")?.slots.find(s=>s.meal_type==="dinner")?.meals).toEqual([]);
  await expect(editor.getByText(/2 por confirmar/)).toBeVisible();
  await expect(editor.getByRole("button",{name:"Guardar no plano"})).toBeDisabled();
  await editor.getByLabel("Reutilizar presenças de outra refeição (opcional)").selectOption({index:1});
  await editor.getByRole("button",{name:"Usar apenas presenças"}).click();
  await expect(editor.getByText("1/2 presentes")).toBeVisible();
  const draftState=await editor.locator(".meal-plan-person").evaluateAll(nodes=>
    nodes.map(row=>({
      status:(row.querySelector('.nf-attendance-decision select') as HTMLSelectElement).value,
      label:row.textContent,
    })),
  );
  expect(draftState.find(row=>row.label?.includes("Pessoa QA"))?.status).toBe("present");
  expect(draftState.find(row=>row.label?.includes("Outra pessoa QA"))?.status).toBe("absent");
  await expect(editor.getByRole("button",{name:"Guardar no plano"})).toBeEnabled();
  // No implicit mutation of the target until its explicit save.
  const unsaved=await getJson<typeof before>(request,
    `/families/${familyId}/meal-plan?start_date=2026-11-16&days=7`);
  expect(unsaved.days.find(d=>d.date==="2026-11-20")?.slots.find(s=>s.meal_type==="dinner")?.meals).toEqual([]);
  await editor.getByRole("button",{name:"Guardar no plano",exact:true}).click({timeout:10000});
  await expect(editor).toHaveCount(0);
  const after=await getJson<typeof before>(request,
    `/families/${familyId}/meal-plan?start_date=2026-11-16&days=7`);
  const newMeal=after.days.find(d=>d.date==="2026-11-20")?.slots.find(s=>s.meal_type==="dinner")?.meals[0];
  expect(newMeal?.participants.map(p=>p.person_id)).toEqual([fixture.person.id]);
  expect(newMeal?.participants.some(p=>p.person_id===second.id)).toBe(false);
  const original=after.days.find(d=>d.date===DATE)?.slots.find(s=>s.meal_type==="dinner")?.meals[0];
  expect(original?.id).toBe(fixture.meal.id);
  expect(original?.participants.map(p=>p.person_id)).toEqual([fixture.person.id]);
});

test("attendance tri-state: unconfirmed is not an implicit absence or a writable meal",async ({page,request})=>{
  const fixture=await seed(request);
  await openFamily(page,fixture.family.id,"/#/meals?date=2026-11-18&meal=dinner&mode=week");
  const detail=page.getByRole("dialog");
  await expect(detail).toBeVisible();
  await detail.getByRole("button",{name:"Escolher receita"}).click();
  const editor=page.getByRole("dialog");
  await expect(editor.getByRole("heading",{name:"Jantar",exact:true})).toBeVisible();
  const decision=editor.getByRole("combobox",{name:"Presença"});
  await expect(decision).toHaveValue("unconfirmed");
  await expect(editor.getByText(/1 por confirmar/)).toBeVisible();
  const save=editor.getByRole("button",{name:"Guardar no plano"});
  await expect(save).toBeDisabled();
  await decision.selectOption("absent");
  await expect(save).toBeDisabled(); // No attending person; cannot save an empty attendance set.
  await decision.selectOption("present");
  await expect(save).toBeEnabled();
  const before=await getJson<{days:{date:string,slots:{meal_type:string,meals:{id:string}[]}[]}[]}>(
    request,`/families/${fixture.family.id}/meal-plan?start_date=2026-11-16&days=7`);
  expect(before.days.find(d=>d.date==="2026-11-18")?.slots.find(s=>s.meal_type==="dinner")?.meals).toEqual([]);
  await save.click();
  await expect(editor).toHaveCount(0);
  const after=await getJson<{days:{date:string,slots:{meal_type:string,meals:{participants:{person_id:string}[]}[]}[]}[]}>(
    request,`/families/${fixture.family.id}/meal-plan?start_date=2026-11-16&days=7`);
  expect(after.days.find(d=>d.date==="2026-11-18")?.slots.find(s=>s.meal_type==="dinner")?.meals[0]?.participants.map(p=>p.person_id)).toEqual([fixture.person.id]);
});

test("weekly attendance decisions persist separately, reject invalid people and protect the planned meals",async ({request})=>{
  const fixture=await seed(request);
  const familyId=fixture.family.id;
  const second=await postJson<{id:string}>(request,`/families/${familyId}/persons`,{
    first_name:"Pessoa com presença pendente QA",last_name:null,birth_date:null,
    preferred_locale:"pt-PT",timezone:"Europe/Lisbon",meal_discovery:null,
  });
  const thirdFamily=await postJson<{id:string}>(request,"/families",{
    name:"Família sem acesso QA",timezone:"Europe/Lisbon",
    meal_discovery_sources:["shared_recipes"],delivery_address:null,restaurant_area:null,
  });
  const outsider=await postJson<{id:string}>(request,`/families/${thirdFamily.id}/persons`,{
    first_name:"Pessoa externa QA",last_name:null,birth_date:null,
    preferred_locale:"pt-PT",timezone:"Europe/Lisbon",meal_discovery:null,
  });
  const url=`${API}/families/${familyId}/planning-setup/2026-11-16`;
  const base={
    person_ids:[fixture.person.id,second.id],meal_types:["dinner"],
    excluded_food_item_ids:[],meal_sources:{dinner:"home"},
    attendance:[],expected_version:0,
    attendance_decisions:[{planning_date:DATE,meal_type:"dinner",people:[
      {person_id:fixture.person.id,decision:"present"},
      {person_id:second.id,decision:"unconfirmed"},
    ]}],
  };
  const invalid=await request.put(url,{data:{...base,attendance_decisions:[{
    planning_date:DATE,meal_type:"dinner",people:[{
      person_id:outsider.id,decision:"present",
    }],
  }]}});
  expect(invalid.status()).toBe(422);
  const invalidDate=await request.put(url,{data:{...base,attendance_decisions:[{
    planning_date:"2026-11-23",meal_type:"dinner",people:[{
      person_id:fixture.person.id,decision:"present",
    }],
  }]}});
  expect(invalidDate.status()).toBe(422);
  const duplicateSlot=await request.put(url,{data:{
    ...base,attendance_decisions:[base.attendance_decisions[0],base.attendance_decisions[0]],
  }});
  expect(duplicateSlot.status()).toBe(422);
  const duplicatePerson=await request.put(url,{data:{
    ...base,attendance_decisions:[{
      planning_date:DATE,meal_type:"dinner",people:[
        {person_id:fixture.person.id,decision:"present"},
        {person_id:fixture.person.id,decision:"absent"},
      ],
    }],
  }});
  expect(duplicatePerson.status()).toBe(422);
  const created=await request.put(url,{data:base});
  expect(created.ok(),`Cannot persist family decisions: ${created.status()} ${await created.text()}`).toBe(true);
  const saved=await created.json() as {version:number;attendance_decisions:typeof base.attendance_decisions};
  expect(saved.version).toBe(1);
  expect(saved.attendance_decisions).toEqual(base.attendance_decisions);
  const reopened=await getJson<typeof saved>(request,
    `/families/${familyId}/planning-setup/2026-11-16`);
  expect(reopened.attendance_decisions).toEqual(base.attendance_decisions);
  const resolved={...base,expected_version:saved.version,attendance_decisions:[{
    ...base.attendance_decisions[0]!,people:[
      {person_id:fixture.person.id,decision:"present"},
      {person_id:second.id,decision:"absent"},
    ],
  }]};
  const updated=await request.put(url,{data:resolved});
  expect(updated.ok(),`Cannot update weekly decisions: ${updated.status()} ${await updated.text()}`).toBe(true);
  const current=await updated.json() as typeof saved;
  expect(current.version).toBe(2);
  expect(current.attendance_decisions[0]?.people[1]?.decision).toBe("absent");
  const {attendance_decisions:_omitted, ...legacyFields}=base;
  const legacySave=await request.put(url,{
    data:{...legacyFields,expected_version:current.version},
  });
  expect(legacySave.ok(),`Older client cleared decisions unexpectedly: ${legacySave.status()} ${await legacySave.text()}`).toBe(true);
  const legacyResult=await legacySave.json() as typeof saved;
  expect(legacyResult.attendance_decisions).toEqual(current.attendance_decisions);
  const stale=await request.put(url,{data:{...base,expected_version:1}});
  expect(stale.status()).toBe(409);
  const plan=await getJson<{days:{date:string,slots:{meal_type:string,meals:{id:string,participants:{person_id:string}[]}[]}[]}[]}>(
    request,`/families/${familyId}/meal-plan?start_date=2026-11-16&days=7`);
  const original=plan.days.find(day=>day.date===DATE)?.slots.find(slot=>slot.meal_type==="dinner")?.meals[0];
  expect(original?.id).toBe(fixture.meal.id);
  expect(original?.participants.map(person=>person.person_id)).toEqual([fixture.person.id]);
});

test("UI weekly attendance: confirmation survives a reload without changing saved meal participation",async ({page,request})=>{
  const fixture=await seed(request);
  const familyId=fixture.family.id;
  const second=await postJson<{id:string}>(request,`/families/${familyId}/persons`,{
    first_name:"Segundo membro QA",last_name:null,birth_date:null,
    preferred_locale:"pt-PT",timezone:"Europe/Lisbon",meal_discovery:null,
  });
  await openFamily(page,familyId,"/#/meals?date=2026-11-12&mode=prepare");
  await expect(page.getByRole("heading",{name:"Vamos planear a próxima semana"})).toBeVisible();
  await page.getByLabel("Semana a começar na segunda-feira").fill("2026-11-16");
  await page.getByText("Quem está em cada refeição?",{exact:true}).click();
  const personDecision=page.getByRole("combobox",{name:"Pessoa QA · 2026-11-19 · Jantar · Confirmação"});
  const secondDecision=page.getByRole("combobox",{name:"Segundo membro QA · 2026-11-19 · Jantar · Confirmação"});
  await expect(personDecision).toHaveValue("unconfirmed");
  await personDecision.selectOption("present");
  await secondDecision.selectOption("unconfirmed");
  await page.getByRole("spinbutton",{name:"2026-11-19 · Jantar · Convidados sem perfil"}).fill("2");
  await page.getByRole("button",{name:/Continuar para restrições/}).click();
  await page.getByRole("checkbox",{name:/Revi as pessoas, refeições e exclusões/}).check();
  await page.getByRole("button",{name:/Guardar escolhas e gerar refeições/}).click();
  await expect.poll(async()=>{
    const setup=await getJson<{attendance_decisions:{planning_date:string;meal_type:string;people:{person_id:string;decision:string}[]}[];guest_notices:{planning_date:string;meal_type:string;guest_count:number}[]}>(request,
      `/families/${familyId}/planning-setup/2026-11-16`);
    return setup.attendance_decisions.find(item=>item.planning_date===DATE&&item.meal_type==="dinner")?.people;
  }).toEqual([
    {person_id:fixture.person.id,decision:"present"},
    {person_id:second.id,decision:"unconfirmed"},
  ]);
  const guestSetup=await getJson<{guest_notices:{planning_date:string;meal_type:string;guest_count:number}[]}>(request,
    `/families/${familyId}/planning-setup/2026-11-16`);
  expect(guestSetup.guest_notices).toEqual([{planning_date:DATE,meal_type:"dinner",guest_count:2}]);
  await page.goto("/#/meals?date=2026-11-12&mode=prepare");
  await page.reload(); // Recreate the planning journey rather than retaining its previous step.
  await expect(page.getByRole("heading",{name:"Vamos planear a próxima semana"})).toBeVisible();
  await page.getByLabel("Semana a começar na segunda-feira").fill("2026-11-16");
  await page.getByText("Quem está em cada refeição?",{exact:true}).click();
  await expect(page.getByRole("combobox",{name:"Pessoa QA · 2026-11-19 · Jantar · Confirmação"})).toHaveValue("present");
  await expect(page.getByRole("combobox",{name:"Segundo membro QA · 2026-11-19 · Jantar · Confirmação"})).toHaveValue("unconfirmed");
  await expect(page.getByRole("spinbutton",{name:"2026-11-19 · Jantar · Convidados sem perfil"})).toHaveValue("2");
  const plan=await getJson<{days:{date:string;slots:{meal_type:string;meals:{id:string;participants:{person_id:string}[]}[]}[]}[]}>(
    request,`/families/${familyId}/meal-plan?start_date=2026-11-16&days=7`);
  const original=plan.days.find(day=>day.date===DATE)?.slots.find(slot=>slot.meal_type==="dinner")?.meals[0];
  expect(original?.id).toBe(fixture.meal.id);
  expect(original?.participants.map(person=>person.person_id)).toEqual([fixture.person.id]);
});

test("UI guest context is shown only for the selected dinner during weekly review",async ({page,request})=>{
  const fixture=await seed(request);
  const familyId=fixture.family.id;
  const second=await postJson<{id:string}>(request,`/families/${familyId}/persons`,{
    first_name:"Segundo membro contextual QA",last_name:null,birth_date:null,
    preferred_locale:"pt-PT",timezone:"Europe/Lisbon",meal_discovery:null,
  });
  const setup={
    person_ids:[fixture.person.id,second.id],
    meal_types:["dinner"],
    excluded_food_item_ids:[],
    meal_sources:{dinner:"home"},
    attendance:[],
    attendance_decisions:[{planning_date:DATE,meal_type:"dinner",people:[
      {person_id:fixture.person.id,decision:"present"},
      {person_id:second.id,decision:"unconfirmed"},
    ]}],
    guest_notices:[{planning_date:DATE,meal_type:"dinner",guest_count:2}],
    expected_version:0,
  };
  const saved=await request.put(`${API}/families/${familyId}/planning-setup/2026-11-16`,{data:setup});
  expect(saved.ok(),await saved.text()).toBe(true);
  await openFamily(page,familyId,"/#/meals?date=2026-11-12&mode=prepare");
  await expect(page.getByRole("heading",{name:"Vamos planear a próxima semana"})).toBeVisible();
  await page.getByLabel("Semana a começar na segunda-feira").fill("2026-11-16");
  await page.getByRole("button",{name:/Continuar para restrições/}).click();
  await page.getByRole("checkbox",{name:/Revi as pessoas, refeições e exclusões/}).check();
  await page.getByRole("button",{name:/Guardar escolhas e gerar refeições/}).click();
  const slot=page.getByRole("button",{name:/Prato sintético QA/}).first();
  await expect(slot).toBeVisible();
  await slot.click();
  const drawer=page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  await expect(drawer.getByText("2 convidado(s) sem perfil.",{exact:false})).toBeVisible();
  await expect(drawer.getByText("1 presença(s) por confirmar nesta refeição.",{exact:false})).toBeVisible();
  await drawer.getByRole("button",{name:"Fechar detalhe"}).click();
  await expect(drawer).toHaveCount(0);
  const original=await getJson<{days:{date:string,slots:{meal_type:string,meals:{id:string,participants:{person_id:string}[]}[]}[]}[]}>(request,
    `/families/${familyId}/meal-plan?start_date=2026-11-16&days=7`);
  const planned=original.days.find(d=>d.date===DATE)?.slots.find(s=>s.meal_type==="dinner")?.meals[0];
  expect(planned?.id).toBe(fixture.meal.id);
  expect(planned?.participants.map(p=>p.person_id)).toEqual([fixture.person.id]);
});

test("guest notices are bounded, versioned and do not modify participants or shopping",async ({request})=>{
  const fixture=await seed(request);
  const familyId=fixture.family.id;
  const second=await postJson<{id:string}>(request,`/families/${familyId}/persons`,{
    first_name:"Segundo membro com perfil QA",last_name:null,birth_date:null,
    preferred_locale:"pt-PT",timezone:"Europe/Lisbon",meal_discovery:null,
  });
  const url=`${API}/families/${familyId}/planning-setup/2026-11-16`;
  const base={
    person_ids:[fixture.person.id,second.id],meal_types:["dinner"],
    excluded_food_item_ids:[],attendance:[],attendance_decisions:[],
    guest_notices:[{planning_date:DATE,meal_type:"dinner",guest_count:2}],
    expected_version:0,
  };
  const invalid=await request.put(url,{data:{
    ...base,guest_notices:[{planning_date:DATE,meal_type:"dinner",guest_count:13}],
  }});
  expect(invalid.status()).toBe(422);
  const duplicate=await request.put(url,{data:{
    ...base,guest_notices:[base.guest_notices[0],base.guest_notices[0]],
  }});
  expect(duplicate.status()).toBe(422);
  const outside=await request.put(url,{data:{
    ...base,guest_notices:[{planning_date:"2026-11-23",meal_type:"dinner",guest_count:1}],
  }});
  expect(outside.status()).toBe(422);
  const created=await request.put(url,{data:base});
  expect(created.ok(),`Cannot save guests: ${created.status()} ${await created.text()}`).toBe(true);
  const stored=await created.json() as {version:number;guest_notices:typeof base.guest_notices};
  expect(stored.guest_notices).toEqual(base.guest_notices);
  const fromServer=await getJson<typeof stored>(request,
    `/families/${familyId}/planning-setup/2026-11-16`);
  expect(fromServer.guest_notices).toEqual(base.guest_notices);
  const {guest_notices:_omitted,...legacy}=base;
  const oldClient=await request.put(url,{data:{...legacy,expected_version:stored.version}});
  expect(oldClient.ok()).toBe(true);
  expect((await oldClient.json() as typeof stored).guest_notices).toEqual(base.guest_notices);
  // The headcount is versioned independently from meal participants.
  // An older request must never silently erase a newer explicit guest count.
  const staleGuestUpdate=await request.put(url,{data:{
    ...base,expected_version:stored.version,guest_notices:[
      {planning_date:DATE,meal_type:"dinner",guest_count:3},
    ],
  }});
  expect(staleGuestUpdate.status()).toBe(409);
  const stillStored=await getJson<typeof stored>(request,
    `/families/${familyId}/planning-setup/2026-11-16`);
  expect(stillStored.guest_notices).toEqual(base.guest_notices);
  const changed=await request.put(url,{data:{...base,expected_version:stored.version+1,guest_notices:[]}});
  expect(changed.ok()).toBe(true);
  expect((await changed.json() as typeof stored).guest_notices).toEqual([]);
  const plan=await getJson<{days:{date:string;slots:{meal_type:string;meals:{id:string;participants:{person_id:string}[]}[]}[]}[]}>(
    request,`/families/${familyId}/meal-plan?start_date=2026-11-16&days=7`);
  const original=plan.days.find(row=>row.date===DATE)?.slots.find(slot=>slot.meal_type==="dinner")?.meals[0];
  expect(original?.id).toBe(fixture.meal.id);
  expect(original?.participants.map(person=>person.person_id)).toEqual([fixture.person.id]);
});
