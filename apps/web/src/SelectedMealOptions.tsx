import MealAdaptationFlow from "./MealAdaptationFlow";
import PersonAvatar from "./ui/PersonAvatar";
import type {AvatarPreference} from "./api/avatarTypes";
import type {MealDeliveryProviderKey} from "./api/mealDeliveryTypes";
import {useEffect,useState} from "react";
import type {ReviewRecipe} from "./api/dietaryReviewClient";
import {getPlanningRestrictions, type PlanningRestrictions, type RetailAlternative} from "./api/planningWorkspaceClient";
import type {MealPlanEntry,MealType} from "./api/mealPlanTypes";
import RecipeDietaryReview from "./RecipeDietaryReview";
import MealSourceOptions from "./MealSourceOptions";
import {useI18n} from "./i18n";

export type SelectedMealContext={recipeId:string|null;planningDate:string;mealType:MealType;personIds:string[];appliedChanges:string[];savedMeal?:MealPlanEntry|null;scheduledAt?:string;timezone?:string;portions?:{person_id:string;quantity:string;unit:string}[];onMealSaved?:(result:{shoppingUpdated:boolean})=>Promise<void>|void;onEvaluateDelivery?:(provider:MealDeliveryProviderKey)=>void};
export function selectedBaseRecipe(recipes:ReviewRecipe[],id:string|null){
  return recipes.find(r=>r.id===id || r.active_variants?.some(v=>v.recipe_id===id));
}
export function appliedMealVariant(recipes:ReviewRecipe[],context:SelectedMealContext){
 if(!context.savedMeal||context.savedMeal.recipe_id!==context.recipeId)return undefined;
 return recipes.flatMap(recipe=>recipe.active_variants??[]).find(variant=>variant.recipe_id===context.savedMeal!.recipe_id);
}
export function selectedMealRestrictions(rules:PlanningRestrictions,context:SelectedMealContext):PlanningRestrictions{
  const sources=rules.sources.filter(s=>context.personIds.includes(s.person_id)&&s.dates.includes(context.planningDate)&&s.meal_types.includes(context.mealType));
  return {...rules,sources,excluded_food_item_ids:[...new Set(sources.flatMap(s=>s.food_item_ids))]};
}
export default function SelectedMealOptions({familyId,context,recipes,products,restrictions,people,manualExclusions,onVariantsChanged}:{
  familyId:string;context:SelectedMealContext;recipes:ReviewRecipe[];products:RetailAlternative[];restrictions:PlanningRestrictions;
  people:{id:string;first_name:string;avatar_appearance?:AvatarPreference|null}[];manualExclusions:string[];onVariantsChanged:()=>void;
}){
  const {locale}=useI18n();const pt=locale==="pt-PT";const [editing,setEditing]=useState(false);
  const recipe=selectedBaseRecipe(recipes,context.recipeId);
  const applied=appliedMealVariant(recipes,context);const [changingApplied,setChangingApplied]=useState(false);
  useEffect(()=>setChangingApplied(false),[context.savedMeal?.updated_at,context.recipeId]);
  const [liveRules,setLiveRules]=useState(restrictions);const [rulesError,setRulesError]=useState("");const [rulesReady,setRulesReady]=useState(false);const [sourcesOpen,setSourcesOpen]=useState(false);
  const attendeeKey=context.personIds.join(",");
  useEffect(()=>{
    let cancelled=false;setRulesError("");setRulesReady(false);setEditing(false);setSourcesOpen(false);
    if(!context.personIds.length) return;
    const day=new Date(`${context.planningDate}T12:00:00Z`);day.setUTCDate(day.getUTCDate()-(day.getUTCDay()+6)%7);
    void getPlanningRestrictions(familyId,{week_start:day.toISOString().slice(0,10),version:0,person_ids:context.personIds,meal_types:[context.mealType],excluded_food_item_ids:[]}).then(r=>{if(!cancelled){setLiveRules(r);setRulesReady(true);}}).catch(e=>{if(!cancelled)setRulesError(String(e));});
    return()=>{cancelled=true;};
  },[familyId,context.planningDate,context.mealType,attendeeKey]);
  const rules=selectedMealRestrictions(liveRules,context);
  const excluded=[...new Set([...manualExclusions,...rules.excluded_food_item_ids])];
  return <section className="nf-selected-options" aria-label={pt?"Opções da refeição selecionada":"Selected meal options"}>
    <div className="nf-meal-attendees"><span>{pt ? "À mesa nesta refeição" : "At this meal"}</span>{people.filter(person=>context.personIds.includes(person.id)).map(person=><span className="nf-attendee-chip" key={person.id}><PersonAvatar identity={person.id} familyIdentity={familyId} name={person.first_name} appearance={person.avatar_appearance} size="sm" decorative/>{person.first_name}</span>)}</div>
    {!context.personIds.length && <p role="status">{pt ? "Escolhe as pessoas presentes para avaliar esta refeição." : "Choose attendees to assess this meal."}</p>}
    {context.personIds.length>0 && !rulesReady && !rulesError && <p role="status">{pt ? "A confirmar as restrições das pessoas presentes…" : "Checking attendees’ restrictions…"}</p>}
    {rulesError && <p role="alert">{pt?"Não foi possível atualizar as restrições desta refeição: ":"Could not refresh restrictions for this meal: "}{rulesError}</p>}
    {context.appliedChanges.length>0&&!applied&&<p className="decision-result" role="status">{pt?"Esta refeição já tem uma adaptação aplicada no plano.":"This meal already has an adaptation applied in the planner."}</p>}
    {recipe && rulesReady && <>
      {applied&&!changingApplied?<section className="decision-result" aria-label={pt?"Refeição confirmada":"Confirmed meal"}><h3>{pt?"Confirmada no plano · trocas aplicadas":"Confirmed in planner · changes applied"}</h3><strong>{applied.name}</strong>{applied.operations.map(op=><p key={op.recipe_ingredient_id}>{recipe.ingredients.find(i=>i.id===op.recipe_ingredient_id)?.name} → {op.replacement_name} · {op.quantity} {op.unit}</p>)}<button type="button" className="button ghost small" onClick={()=>setChangingApplied(true)}>{pt?"Alterar esta adaptação":"Change this adaptation"}</button></section>:<MealAdaptationFlow key={`${familyId}:${context.planningDate}:${context.mealType}:${context.recipeId}`} familyId={familyId} recipe={recipe} context={context} people={people} excluded={excluded} onVariantsChanged={onVariantsChanged}/>}

      {(!applied||changingApplied)&&<button type="button" className="button ghost" onClick={()=>setEditing(v=>!v)}>{pt?"Rever ingredientes deste prato":"Review this dish's ingredients"}</button>}
      {editing && (!applied||changingApplied) && <RecipeDietaryReview familyId={familyId} recipeId={recipe.id} planningDate={context.planningDate} mealType={context.mealType} personIds={context.personIds} onVariantsChanged={onVariantsChanged}/>}
    </>}
    {rulesReady && <details className="nf-meal-source-tools" onToggle={event=>setSourcesOpen(event.currentTarget.open)}><summary>{pt ? "Explorar outras origens · restaurante ou entrega" : "Explore other sources · restaurant or delivery"}</summary>{sourcesOpen && <MealSourceOptions key={`${familyId}:${context.planningDate}:${context.mealType}`} familyId={familyId} context={context} people={people.filter(p=>context.personIds.includes(p.id))} restrictions={rules}/>}</details>}
  </section>;
}
