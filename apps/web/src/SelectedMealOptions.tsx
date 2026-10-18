import type {MealDeliveryProviderKey} from "./api/mealDeliveryTypes";
import {useEffect,useState} from "react";
import type {ReviewRecipe} from "./api/dietaryReviewClient";
import {getPlanningRestrictions, type PlanningRestrictions, type RetailAlternative} from "./api/planningWorkspaceClient";
import type {MealType} from "./api/mealPlanTypes";
import RecipeAdaptationCards from "./RecipeAdaptationCards";
import RecipeDietaryReview from "./RecipeDietaryReview";
import MealSourceOptions from "./MealSourceOptions";
import {useI18n} from "./i18n";

export type SelectedMealContext={recipeId:string|null;planningDate:string;mealType:MealType;personIds:string[];appliedChanges:string[];onEvaluateDelivery?:(provider:MealDeliveryProviderKey)=>void};
export function selectedBaseRecipe(recipes:ReviewRecipe[],id:string|null){
  return recipes.find(r=>r.id===id || r.active_variants?.some(v=>v.recipe_id===id));
}
export function selectedMealRestrictions(rules:PlanningRestrictions,context:SelectedMealContext):PlanningRestrictions{
  const sources=rules.sources.filter(s=>context.personIds.includes(s.person_id)&&s.dates.includes(context.planningDate)&&s.meal_types.includes(context.mealType));
  return {...rules,sources,excluded_food_item_ids:[...new Set(sources.flatMap(s=>s.food_item_ids))]};
}
export default function SelectedMealOptions({familyId,context,recipes,products,restrictions,people,manualExclusions,onVariantsChanged}:{
  familyId:string;context:SelectedMealContext;recipes:ReviewRecipe[];products:RetailAlternative[];restrictions:PlanningRestrictions;
  people:{id:string;first_name:string}[];manualExclusions:string[];onVariantsChanged:()=>void;
}){
  const {locale}=useI18n();const pt=locale==="pt-PT";const [editing,setEditing]=useState(false);
  const recipe=selectedBaseRecipe(recipes,context.recipeId);
  const [liveRules,setLiveRules]=useState(restrictions);const [rulesError,setRulesError]=useState("");
  const attendeeKey=context.personIds.join(",");
  useEffect(()=>{
    let cancelled=false;setRulesError("");
    if(!context.personIds.length) return;
    const day=new Date(`${context.planningDate}T12:00:00Z`);day.setUTCDate(day.getUTCDate()-(day.getUTCDay()+6)%7);
    void getPlanningRestrictions(familyId,{week_start:day.toISOString().slice(0,10),version:0,person_ids:context.personIds,meal_types:[context.mealType],excluded_food_item_ids:[]}).then(r=>{if(!cancelled)setLiveRules(r);}).catch(e=>{if(!cancelled)setRulesError(String(e));});
    return()=>{cancelled=true;};
  },[familyId,context.planningDate,context.mealType,attendeeKey]);
  const rules=selectedMealRestrictions(liveRules,context);
  const excluded=[...new Set([...manualExclusions,...rules.excluded_food_item_ids])];
  return <section aria-label={pt?"Opções da refeição selecionada":"Selected meal options"}>
    {rulesError && <p role="alert">{pt?"Não foi possível atualizar as restrições desta refeição: ":"Could not refresh restrictions for this meal: "}{rulesError}</p>}
    {recipe && <>
      {!context.appliedChanges.length && <><h4>{pt?"Trocas propostas para este prato":"Proposed substitutions for this dish"}</h4><RecipeAdaptationCards compact includeProposals recipes={[recipe]} excluded={excluded} products={products} restrictions={rules} people={people.filter(p=>context.personIds.includes(p.id))}/></>}
      <button type="button" className="button ghost" onClick={()=>setEditing(v=>!v)}>{pt?"Rever ingredientes deste prato":"Review this dish's ingredients"}</button>
      {editing && <RecipeDietaryReview familyId={familyId} recipeId={recipe.id} planningDate={context.planningDate} mealType={context.mealType} personIds={context.personIds} onVariantsChanged={onVariantsChanged}/>}
    </>}
    <MealSourceOptions key={`${familyId}:${context.planningDate}:${context.mealType}`} familyId={familyId} context={context} people={people.filter(p=>context.personIds.includes(p.id))} restrictions={rules}/>
  </section>;
}
