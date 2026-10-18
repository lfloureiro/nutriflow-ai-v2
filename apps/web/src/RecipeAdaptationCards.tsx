import { useState } from "react";
import type { ReviewRecipe } from "./api/dietaryReviewClient";
import type { PlanningRestrictions, RetailAlternative } from "./api/planningWorkspaceClient";
import RetailAlternativeCards from "./RetailAlternativeCards";
import { useI18n } from "./i18n";

export function affectedRecipes(recipes: ReviewRecipe[], excluded: string[], includeProposals=false) {
  const ids = new Set(excluded);
  return recipes.map(recipe => ({recipe, ingredients:recipe.ingredients.filter(i=>ids.has(i.food_item_id) || (includeProposals && i.substitutions.some(s=>s.status!=="rejected")))})).filter(row=>row.ingredients.length>0);
}

export function adaptationSummaries(recipes: ReviewRecipe[], excluded: string[]) {
  return Object.fromEntries(affectedRecipes(recipes,excluded).map(({recipe,ingredients})=>[
    recipe.id, ingredients.map(i=>`${i.name} → ${recipe.active_variants?.flatMap(v=>v.operations).find(o=>o.recipe_ingredient_id===i.id)?.replacement_name ?? i.substitutions.find(s=>s.status!=="rejected")?.replacement_name ?? "alternativa por definir"}`),
  ]));
}

export default function RecipeAdaptationCards({recipes, excluded, products, restrictions, people, compact=false, includeProposals=false}: {
  includeProposals?: boolean; compact?: boolean; recipes: ReviewRecipe[]; excluded: string[]; products: RetailAlternative[];
  restrictions: PlanningRestrictions; people: {id:string; first_name:string}[];
}) {
  const {locale} = useI18n(); const pt = locale==="pt-PT";
  const [search,setSearch] = useState("");
  const [showAll,setShowAll] = useState(false);
  const affected = affectedRecipes(recipes,excluded,includeProposals);
  return <section className="journey-card recipe-adaptation-cards">
    {!compact && <><h2>{pt ? "As nossas receitas, com as trocas à vista" : "Our recipes, with visible substitutions"}</h2>
    <p>{pt ? "Mantemos a receita base. Consulta as variantes preparadas e as propostas de troca; o estado e as quantidades em falta são indicados em cada ingrediente." : "Keep the base recipe. See prepared variants and substitution proposals; status and missing quantities are shown for each ingredient."}</p>
    <label className="field"><span>{pt ? "Encontrar receita" : "Find recipe"}</span><input type="search" value={search} onChange={e=>setSearch(e.target.value)}/></label>
    <p className="muted">{affected.length} {pt ? "receitas com ingredientes a adaptar" : "recipes with ingredients to adapt"}</p>
    </>}
    <div className="adaptation-card-list">{affected.filter(({recipe})=>recipe.name.toLocaleLowerCase().includes(search.toLocaleLowerCase())).slice(0,showAll||search ? undefined:6).map(({recipe,ingredients})=><article className="adaptation-base-card" key={recipe.id}>
      <h3>{recipe.name}</h3><strong className="adaptation-state">{recipe.active_variants?.length ? (pt ? "Receita base · variantes ativas no catálogo" : "Base recipe · active catalogue variants") : (pt ? "Receita base · adaptação proposta" : "Base recipe · proposed adaptation")}</strong>
      {ingredients.map(i=>{
        const options=i.substitutions.filter(s=>s.status!=="rejected");
        const activeOptions=(recipe.active_variants??[]).flatMap(v=>v.operations.filter(o=>o.recipe_ingredient_id===i.id).map(o=>({...o,variantName:v.name,variantId:v.id})));
        const reasons=restrictions.sources.filter(s=>s.food_item_ids.includes(i.food_item_id));
        return <div key={i.id} className="adaptation-change">
          <p><strong>{i.name} → {activeOptions[0]?.replacement_name ?? options[0]?.replacement_name ?? (pt ? "alternativa por definir" : "alternative needed")}</strong></p>
          <small>{reasons.map(s=>`${people.find(p=>p.id===s.person_id)?.first_name??""} · ${s.label}`).join("; ") || (excluded.includes(i.food_item_id) ? (pt ? "Exclusão adicional da semana" : "Additional weekly exclusion") : (pt ? "Proposta registada; necessidade e dose por confirmar" : "Saved proposal; need and portion remain unconfirmed"))}</small>
          {activeOptions.map(o=><p key={o.variantId}><strong>{o.variantName}</strong> · {o.quantity} {o.unit} · {o.preparation}<br/>{pt?"Variante ativa no catálogo; o planeador reavalia as pessoas e porções.":"Active catalogue variant; the planner rechecks people and portions."}</p>)}
          {!options.length && !activeOptions.length && <p role="status">{pt ? "Ainda não existe uma alternativa revista para este ingrediente." : "No reviewed alternative exists for this ingredient yet."}</p>}
          {options.map((option,index)=><div key={option.id}>
            {index>0 && <p><strong>{pt ? "Outra opção: " : "Another option: "}{option.replacement_name}</strong></p>}
            <p className="muted">{option.status==="reviewed" ? (pt ? "Revista" : "Reviewed") : (pt ? "Proposta por rever" : "Proposal to review")} · {option.replacement_quantity ? `${option.replacement_quantity} ${option.replacement_unit}` : (pt ? "Quantidade por definir; não aplicar grama por grama" : "Quantity needed; do not replace gram for gram")}</p>
            <p>{option.notes}</p>
          </div>)}
          <details><summary>{pt ? "Alternativas de supermercado" : "Supermarket alternatives"}</summary><RetailAlternativeCards products={products.filter(p=>p.applicable_food_item_ids.includes(i.food_item_id))}/></details>
        </div>;
      })}
    </article>)}</div>
    {affected.length>6 && !search && <button type="button" className="button ghost" onClick={()=>setShowAll(v=>!v)}>{showAll ? (pt ? "Mostrar menos":"Show fewer") : (pt ? "Ver todas as receitas":"Show all recipes")}</button>}
    {!affected.length && <p>{pt ? "Não há trocas identificadas para as exclusões atuais. Isto não certifica doses nem produtos compostos." : "No substitutions were identified for current exclusions. This does not certify portions or compound products."}</p>}
  </section>;
}
