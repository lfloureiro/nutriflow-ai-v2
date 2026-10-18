import {describe,it,expect,vi} from "vitest";
import {renderToStaticMarkup} from "react-dom/server";
import SelectedMealOptions,{selectedBaseRecipe,selectedMealRestrictions,type SelectedMealContext} from "./SelectedMealOptions";
import type {ReviewRecipe} from "./api/dietaryReviewClient";
import type {PlanningRestrictions} from "./api/planningWorkspaceClient";
import {providerCanSync,deliveryDestinations} from "./MealSourceOptions";
import {guidedMealSources} from "./WeeklyProposalPreview";
import {recommendationDeliveryProviderKeys} from "./recommendationPlanning";
import type {MealDiscoveryCapability} from "./api/setupTypes";
vi.mock("./i18n",()=>({useI18n:()=>({locale:"pt-PT"})}));
const recipes=[{id:"selected",name:"Escalopes",ingredients:[{id:"flour",food_item_id:"f",name:"Farinha",substitutions:[{id:"s",replacement_name:"Espessante de arroz",status:"proposed",replacement_quantity:null,notes:"Dose por validar"}]}],active_variants:[{id:"v",recipe_id:"projection",name:"Variante",operations:[]}]},{id:"other",name:"Almondegas",ingredients:[]}] as unknown as ReviewRecipe[];
const context:SelectedMealContext={recipeId:"selected",planningDate:"2026-10-20",mealType:"dinner",personIds:["p","b"],appliedChanges:[]};
const rules:PlanningRestrictions={excluded_food_item_ids:["unrelated"],warnings:[],sources:[{person_id:"p",source_id:"s",source_kind:"condition",label:"SIBO",food_item_ids:["unrelated"],dates:["2026-10-20"],meal_types:["dinner"]}]};
describe("selected dish substitutions and delivery",()=>{
  it("shows proposals for the selected dish even when the ingredient has no high-FODMAP link",()=>{
    const html=renderToStaticMarkup(<SelectedMealOptions familyId="family" context={context} recipes={recipes} products={[]} restrictions={rules} people={[{id:"p",first_name:"Ana"}]} manualExclusions={[]} onVariantsChanged={()=>{}}/>);
    expect(html).toContain("Farinha → Espessante de arroz");
    expect(html).toContain("Quantidade por definir");
    expect(html).toContain("necessidade e dose por confirmar");
    expect(html).not.toContain("Almondegas");
    expect(html).not.toContain("Encontrar receita");
    expect(html).not.toContain("Ver todas as receitas");
  });
  it("resolves a projected variant back to its own base and never defaults to another recipe",()=>{
    expect(selectedBaseRecipe(recipes,"projection")?.id).toBe("selected");
    expect(selectedBaseRecipe(recipes,"missing")).toBeUndefined();
    expect(selectedBaseRecipe(recipes,null)).toBeUndefined();
  });
  it("filters disease context by actual people, date and meal",()=>{
    expect(selectedMealRestrictions(rules,context).sources).toHaveLength(1);
    expect(selectedMealRestrictions(rules,{...context,personIds:["b"]}).sources).toEqual([]);
    expect(selectedMealRestrictions(rules,{...context,mealType:"lunch"}).sources).toEqual([]);
    expect(selectedMealRestrictions(rules,{...context,planningDate:"2026-10-21"}).sources).toEqual([]);
  });
  it("does not present proposed swaps as applied when the selected variant already carries changes",()=>{
    const html=renderToStaticMarkup(<SelectedMealOptions familyId="family" context={{...context,recipeId:"projection",appliedChanges:["Farinha → Arroz"]}} recipes={recipes} products={[]} restrictions={rules} people={[]} manualExclusions={[]} onVariantsChanged={()=>{}}/>);
    expect(html).not.toContain("Trocas propostas");
    expect(html).toContain("Rever ingredientes deste prato");
  });
  it("uses delivery for guided lunches and preserves an explicit home choice",()=>{
    expect(guidedMealSources("lunch",{})).toEqual(["uber_eats","glovo","bolt_food"]);
    expect(guidedMealSources("lunch",{lunch:"home"})).toEqual(["cooked"]);
    expect(guidedMealSources("dinner",{})).toEqual(["cooked"]);
    expect(guidedMealSources("lunch",{lunch:"restaurant"})).toEqual(["restaurant"]);
    expect(recommendationDeliveryProviderKeys(["glovo"])).toEqual(["glovo"]);
  });
  it("requires a selected live supported provider and keeps health details out of platform URLs",()=>{
    const cap={selected:true,live:true,supported:true} as MealDiscoveryCapability;
    expect(providerCanSync(cap)).toBe(true);
    expect(providerCanSync({...cap,live:false})).toBe(false);
    expect(providerCanSync({...cap,selected:false})).toBe(false);
    expect(providerCanSync(undefined)).toBe(false);
    expect(deliveryDestinations).toHaveLength(3);
    expect(deliveryDestinations.every(p=>new URL(p.url).search==="")).toBe(true);
  });
});
