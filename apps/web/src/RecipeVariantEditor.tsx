import { useEffect,useState } from "react";
import { listFamilyIngredients,listFamilyPersons } from "./api/client";
import type { Ingredient } from "./api/ingredientTypes";
import type { Person } from "./api/types";
import type { MealType } from "./api/mealPlanTypes";
import type { ReviewRecipe } from "./api/dietaryReviewClient";
import {activateRecipeVariant,createRecipeVariant,listRecipeVariants,retireRecipeVariant,validateRecipeVariant,type RecipeVariant,type VariantOperation,type VariantValidation} from "./api/recipeVariantClient";
import {useI18n} from "./i18n";

export function variantDraftIssues(servings:string,operations:VariantOperation[]) {
  const issues:string[]=[];
  if(!Number.isFinite(Number(servings))||Number(servings)<=0) issues.push("servings");
  if(!operations.length) issues.push("operations");
  for(const op of operations) if(!op.replacement_food_item_id||!Number.isFinite(Number(op.quantity))||Number(op.quantity)<=0||!op.preparation.trim()) issues.push(op.recipe_ingredient_id);
  return issues;
}

export default function RecipeVariantEditor({familyId,recipe,planningDate,personIds,onChanged,mealType}:{familyId:string;mealType?:MealType;recipe:ReviewRecipe;planningDate?:string;personIds?:string[];onChanged?:()=>void}){
  const {locale}=useI18n();const pt=locale==="pt-PT";
  const [foods,setFoods]=useState<Ingredient[]>([]);const [people,setPeople]=useState<Person[]>([]);const [variants,setVariants]=useState<RecipeVariant[]>([]);
  const [operations,setOperations]=useState<Record<string,VariantOperation>>({});const [name,setName]=useState("");const [servings,setServings]=useState(recipe.serving_count??"");
  const [date,setDate]=useState(planningDate??new Intl.DateTimeFormat("sv-SE",{timeZone:"Europe/Lisbon"}).format(new Date()));
  const [meal,setMeal]=useState<MealType>(mealType??"dinner");const [selected,setSelected]=useState<string[]>(personIds??[]);
  const [revisionOf,setRevisionOf]=useState("");const [checks,setChecks]=useState<Record<string,VariantValidation>>({});const [error,setError]=useState("");const [busy,setBusy]=useState(false);const [loading,setLoading]=useState(true);
  const [notice,setNotice]=useState("");
  useEffect(()=>{let cancelled=false;setLoading(true);setFoods([]);setPeople([]);setVariants([]);setChecks({});setError("");setOperations({});setName("");setRevisionOf("");setServings(recipe.serving_count??"");setSelected(personIds??[]);
    void Promise.all([listFamilyIngredients(familyId),listFamilyPersons(familyId),listRecipeVariants(familyId,recipe.id)]).then(([f,p,v])=>{if(!cancelled){setFoods(f);setPeople(p);setVariants(v);}}).catch(e=>{if(!cancelled)setError(String(e));}).finally(()=>{if(!cancelled)setLoading(false);});
    return()=>{cancelled=true;};
  },[familyId,recipe.id]);
  const ops=Object.values(operations);const draftIssues=variantDraftIssues(servings,ops);
  function invalidate(){setChecks({});setNotice("");}
  async function run(action:()=>Promise<void>){setBusy(true);setError("");setNotice("");try{await action();}catch(e){setError(String(e));}finally{setBusy(false);}}
  async function refresh(){setVariants(await listRecipeVariants(familyId,recipe.id));onChanged?.();}
  return <section className="journey-card" aria-label={pt?"Variante completa da receita":"Complete recipe variant"}>
    <h3>{pt?"Variante familiar completa":"Complete Family variant"}</h3>
    <p>{pt?"Escolhe todas as trocas necessárias, identifica os ingredientes concretos e confirma as quantidades para a receita inteira. Guardar cria um rascunho; só uma variante validada pode ser ativada para aparecer no planeamento.":"Choose every required change, identify the actual ingredients and confirm whole-recipe quantities. Saving creates a draft; only a validated variant can be activated for planning."}</p>
    <button type="button" className="button secondary small" disabled={busy||loading} onClick={()=>void run(async()=>{setFoods(await listFamilyIngredients(familyId));setNotice(pt?"Ingredientes atualizados. Já podes escolher os produtos confirmados.":"Ingredients refreshed. Confirmed products are now available to select.");})}>{pt?"Atualizar ingredientes":"Refresh ingredients"}</button>
    {loading&&<p role="status">{pt?"A carregar ingredientes e variantes…":"Loading ingredients and variants…"}</p>}
    {error&&<p role="alert" className="error-banner">{error}</p>}{notice&&<p role="status">{notice}</p>}
    <details><summary>{pt?"Preparar nova variante ou revisão":"Prepare a new variant or revision"}</summary>
      <form className="dietary-form" onSubmit={e=>{e.preventDefault();void run(async()=>{await createRecipeVariant(familyId,{base_recipe_id:recipe.id,name,serving_count:servings,operations:ops,...(revisionOf?{revises_variant_id:revisionOf}:{})});await refresh();setNotice(pt?"Rascunho guardado. Valida para as pessoas e a refeição abaixo.":"Draft saved. Validate it for the people and meal below.");});}}>
        <label>{pt?"Nome da variante":"Variant name"}<input required maxLength={100} value={name} disabled={busy} onChange={e=>setName(e.target.value)}/></label>
        <label>{pt?"Número de doses confirmado":"Confirmed serving count"}<input required type="number" min="0.01" max="999999" step="0.01" value={servings} disabled={busy} onChange={e=>setServings(e.target.value)}/></label>
        <label>{pt?"Nova variante ou revisão de":"New variant or revision of"}<select value={revisionOf} disabled={busy} onChange={e=>setRevisionOf(e.target.value)}><option value="">{pt?"Nova variante independente":"New independent variant"}</option>{variants.map(v=><option key={v.id} value={v.id}>{v.name} · r{v.revision}</option>)}</select></label>
        {recipe.ingredients.map(i=><fieldset className="dietary-wide" key={i.id}><legend><label><input type="checkbox" disabled={busy} checked={!!operations[i.id]} onChange={e=>setOperations(old=>{const next={...old};if(e.target.checked){const suggested=i.substitutions.find(s=>s.status!=="rejected");next[i.id]={recipe_ingredient_id:i.id,replacement_food_item_id:suggested?.replacement_food_item_id??"",quantity:suggested?.replacement_quantity??"",unit:suggested?.replacement_unit??"g",preparation:""};}else delete next[i.id];return next;})}/>{i.name} · {i.quantity} {i.unit}</label></legend>
          {operations[i.id]&&<div className="dietary-form">
            <label>{pt?"Ingrediente alternativo identificado":"Identified replacement ingredient"}<select required disabled={busy} value={operations[i.id]!.replacement_food_item_id} onChange={e=>setOperations(old=>({...old,[i.id]:{...old[i.id]!,replacement_food_item_id:e.target.value}}))}><option value="">{pt?"Escolher no catálogo":"Choose from catalogue"}</option>{foods.filter(f=>f.id!==i.food_item_id).map(f=><option value={f.id} key={f.id}>{f.name}{f.brand?` · ${f.brand}`:""}{!f.latest_composition?" · sem composição":""}</option>)}</select></label>
            <label>{pt?"Quantidade na receita inteira":"Whole-recipe quantity"}<input required disabled={busy} type="number" min="0.0001" max="9999999999" step="0.0001" value={operations[i.id]!.quantity} onChange={e=>setOperations(old=>({...old,[i.id]:{...old[i.id]!,quantity:e.target.value}}))}/></label>
            <label>{pt?"Unidade":"Unit"}<select disabled={busy} value={operations[i.id]!.unit} onChange={e=>setOperations(old=>({...old,[i.id]:{...old[i.id]!,unit:e.target.value}}))}>{["g","ml","un","serving"].map(u=><option key={u}>{u}</option>)}</select></label>
            <label>{pt?"Preparação da alternativa":"Replacement preparation"}<input required disabled={busy} maxLength={160} value={operations[i.id]!.preparation} onChange={e=>setOperations(old=>({...old,[i.id]:{...old[i.id]!,preparation:e.target.value}}))}/></label>
          </div>}
        </fieldset>)}
        <button type="submit" className="button primary" disabled={loading||busy||!!draftIssues.length||!name.trim()}>{pt?"Guardar variante em rascunho":"Save variant draft"}</button>
      </form>
    </details>
    <fieldset disabled={busy}><legend>{pt?"Validar para esta refeição e pessoas":"Validate for this meal and people"}</legend>
      <div className="dietary-form"><label>{pt?"Data de validação":"Validation date"}<input type="date" value={date} onChange={e=>{setDate(e.target.value);invalidate();}}/></label>
      <label>{pt?"Tipo de refeição":"Meal type"}<select value={meal} onChange={e=>{setMeal(e.target.value as MealType);invalidate();}}>{(["breakfast","lunch","snack","dinner"] as MealType[]).map(m=><option key={m}>{m}</option>)}</select></label></div>
      <div className="journey-checks">{people.map(p=><label key={p.id}><input type="checkbox" checked={selected.includes(p.id)} onChange={e=>{setSelected(old=>e.target.checked?[...old,p.id]:old.filter(id=>id!==p.id));invalidate();}}/>{p.first_name}</label>)}</div>
      <p>{pt?"Validação inicial com uma dose por pessoa; o planeador reavalia as porções e restrições reais em cada refeição. Não constitui certificação FODMAP por dose.":"Initial validation uses one serving per person; the planner rechecks actual portions and restrictions for each meal. This is not portion-specific FODMAP certification."}</p>
    </fieldset>
    {variants.map(v=><article className="dietary-substitution" key={v.id}><h4>{v.name} · r{v.revision} · {v.status}</h4>
      {v.operations.map(o=><p key={o.recipe_ingredient_id}><strong>{o.source_name} → {o.replacement_name}</strong> · {o.quantity} {o.unit} · {o.preparation}</p>)}
      <p>{v.serving_count} {pt?"doses":"servings"} · {v.energy_per_serving??"?"} kcal/{pt?"dose":"serving"}</p>
      {v.issues.map((issue,index)=><p role="status" key={index}>{issue}</p>)}
      {checks[v.id]&&<div role="status"><strong>{checks[v.id]!.eligible?(pt?"Elegível para o contexto verificado":"Eligible for the checked context"):(pt?"Existem impedimentos":"There are blockers")}</strong>{checks[v.id]!.issues.map((i,n)=><p key={n}>{i}</p>)}{checks[v.id]!.participants.map(p=><p key={p.person_id}>{people.find(person=>person.id===p.person_id)?.first_name}: {p.eligible?(pt?"sem impedimento registado":"no recorded blocker"):p.issues.join("; ")}</p>)}</div>}
      <div className="dietary-actions"><button type="button" disabled={loading||busy||!selected.length||!date||v.status==="retired"} onClick={()=>void run(async()=>{const result=await validateRecipeVariant(familyId,v,{expected_version:v.version,planning_date:date,meal_type:meal,participants:selected.map(person_id=>({person_id,quantity:"1"}))});setChecks(old=>({...old,[v.id]:result}));})}>{pt?"Validar conjunto":"Validate all changes"}</button>
      <button type="button" disabled={busy||loading||!checks[v.id]?.eligible||v.status!=="draft"} onClick={()=>void run(async()=>{await activateRecipeVariant(familyId,v,{expected_version:v.version,planning_date:date,meal_type:meal,participants:selected.map(person_id=>({person_id,quantity:"1"}))});setChecks({});await refresh();setNotice(pt?"Variante ativa. Recalcula a proposta semanal para a incluir.":"Variant active. Recalculate the weekly proposal to include it.");})}>{pt?"Ativar no planeamento":"Activate for planning"}</button>
      <button type="button" disabled={busy||v.status==="retired"} onClick={()=>void run(async()=>{await retireRecipeVariant(familyId,v);setChecks({});await refresh();})}>{pt?"Retirar variante":"Retire variant"}</button></div>
    </article>)}
  </section>;
}
