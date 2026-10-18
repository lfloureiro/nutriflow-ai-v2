import IngredientAlternativeLine from "./IngredientAlternativeLine";
import { useEffect, useState } from "react";
import {
  createSubstitution, listFodmapReferences, listRecipeReviews, reviewSubstitution,
  type FodmapReference, type ReviewIngredient, type ReviewRecipe, type Substitution,
} from "./api/dietaryReviewClient";
import { useI18n } from "./i18n";
import "./dietary-review.css";
import "./planning-journey.css";
import { listRetailAlternatives, type RetailAlternative } from "./api/planningWorkspaceClient";
import RetailAlternativeCards from "./RetailAlternativeCards";
import RecipeVariantEditor from "./RecipeVariantEditor";

export function reviewCounts(rows: ReviewRecipe[]) {
  return {
    recipes: rows.length,
    proposals: rows.reduce((n, r) => n + r.ingredients.reduce((sum, i) => sum + i.substitutions.filter(s => s.status !== "rejected").length, 0), 0),
    missingIngredients: rows.filter(r => !r.ingredients.length).length,
  };
}

function SubstitutionCard({row, familyId, reference, onChanged}: {
  row: Substitution; familyId: string; reference?: FodmapReference; onChanged: () => void;
}) {
  const {locale} = useI18n(); const pt = locale === "pt-PT";
  const [notes, setNotes] = useState(row.notes); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const [quantity,setQuantity] = useState(row.replacement_quantity??"");
  const [unit,setUnit] = useState(row.replacement_unit??"g");
  const statuses = pt ? {proposed: "Por rever", reviewed: "Revista — sem aplicação", rejected: "Rejeitada"}
    : {proposed: "To review", reviewed: "Reviewed — not applied", rejected: "Rejected"};
  function save(status: Substitution["status"]) {
    setBusy(true); setError("");
    void reviewSubstitution(familyId, row, status, notes, {replacement_quantity:quantity||null,replacement_unit:quantity ? unit:null}).then(onChanged)
      .catch(e => setError(String(e))).finally(() => setBusy(false));
  }
  return <div className="dietary-substitution">
    <strong>→ {row.replacement_name}</strong> <span className="dietary-badge">{statuses[row.status]}</span>
    <p>{row.replacement_quantity ? `${new Intl.NumberFormat(locale).format(Number(row.replacement_quantity))} ${row.replacement_unit}` : pt ? "Quantidade por definir; sem equivalência nutricional calculada." : "Quantity to be defined; nutritional equivalence has not been calculated."}</p>
    <p className="dietary-notes">{row.notes}</p>
    {reference && <p><a href={reference.source_url} target="_blank" rel="noreferrer">{reference.source_name} · {pt ? reference.name_pt : reference.name_en}</a></p>}
    <details><summary>{pt ? "Rever proposta" : "Review proposal"}</summary>
      <label className="dietary-filter">{pt ? "Quantidade alternativa na receita completa" : "Replacement quantity for the whole recipe"}<input type="number" min="0.0001" max="9999999999" step="0.0001" value={quantity} onChange={e=>setQuantity(e.target.value)} disabled={busy}/></label>
      <label className="dietary-filter">{pt ? "Unidade da alternativa" : "Replacement unit"}<select value={unit} onChange={e=>setUnit(e.target.value)} disabled={busy}><option value="g">g</option><option value="ml">ml</option><option value="un">{pt ? "Unidade":"Unit"}</option><option value="serving">{pt ? "Porção":"Serving"}</option></select></label>
      <p className="dietary-help">{pt ? "Usa a quantidade para a receita completa, não por pessoa. Deixa vazio se ainda não está definida; não é assumida equivalência com o ingrediente original." : "Use the whole-recipe quantity, not a per-person amount. Leave blank if unknown; equivalence with the original ingredient is not assumed."}</p>
      <label className="dietary-filter">{pt ? "Notas da revisão" : "Review notes"}<textarea maxLength={5000} value={notes} onChange={e => setNotes(e.target.value)} /></label>
      <p className="dietary-help">{pt ? "Marcar como revista organiza o trabalho; não valida adequação clínica nem altera a receita." : "Marking as reviewed organizes the work; it does not validate clinical suitability or change the recipe."}</p>
      <div className="dietary-actions">
        <button type="button" disabled={busy} onClick={() => save("reviewed")}>{pt ? "Guardar revisão" : "Save review"}</button>
        <button type="button" disabled={busy} onClick={() => save("rejected")}>{pt ? "Rejeitar" : "Reject"}</button>
        <button type="button" disabled={busy} onClick={() => save("proposed")}>{pt ? "Voltar a rever" : "Return to review"}</button>
      </div>
    </details>
    {error && <p role="alert">{error}</p>}
  </div>;
}

function NewSubstitution({ingredient, familyId, references, onChanged}: {
  ingredient: ReviewIngredient; familyId: string; references: FodmapReference[]; onChanged: () => void;
}) {
  const {locale} = useI18n(); const pt = locale === "pt-PT";
  const [name, setName] = useState(""); const [notes, setNotes] = useState("");
  const [ref, setRef] = useState(""); const [quantity, setQuantity] = useState(""); const [unit, setUnit] = useState("g");
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  return <details><summary>{pt ? "Propor outra substituição" : "Propose another substitution"}</summary>
    <form className="dietary-form" onSubmit={e => {
      e.preventDefault(); setBusy(true); setError("");
      void createSubstitution(familyId, {
        recipe_ingredient_id: ingredient.id, replacement_name: name, notes,
        reference_id: ref || null, replacement_quantity: quantity || null, replacement_unit: quantity ? unit : null,
      }).then(() => {setName(""); setNotes(""); setQuantity(""); onChanged();})
        .catch(e => setError(String(e))).finally(() => setBusy(false));
    }}>
      <label>{pt ? "Ingrediente alternativo" : "Replacement ingredient"}<input required maxLength={160} value={name} onChange={e => setName(e.target.value)} /></label>
      <label>{pt ? "Quantidade proposta (opcional)" : "Proposed quantity (optional)"}<input type="number" min="0.0001" max="9999999999" step="0.0001" value={quantity} onChange={e => setQuantity(e.target.value)} /></label>
      <label>{pt ? "Unidade" : "Unit"}<select value={unit} onChange={e => setUnit(e.target.value)}><option value="g">g</option><option value="ml">ml</option><option value="un">{pt ? "Unidade" : "Unit"}</option><option value="serving">{pt ? "Porção" : "Serving"}</option></select></label>
      <label>{pt ? "Orientação de referência (opcional)" : "Reference guidance (optional)"}<select value={ref} onChange={e => setRef(e.target.value)}><option value="">{pt ? "Sem referência" : "No reference"}</option>{references.map(r => <option key={r.id} value={r.id}>{pt ? r.name_pt : r.name_en} · {r.source_name}</option>)}</select></label>
      <label className="dietary-wide">{pt ? "Notas / dados por confirmar" : "Notes / missing evidence"}<textarea maxLength={5000} value={notes} onChange={e => setNotes(e.target.value)} /></label>
      <button type="submit" disabled={busy}>{pt ? "Guardar proposta" : "Save proposal"}</button>
      {error && <p role="alert">{error}</p>}
    </form>
  </details>;
}

export default function RecipeDietaryReview({familyId,planningDate,personIds,onVariantsChanged,recipeId,mealType}: {familyId: string;recipeId?:string;mealType?:"breakfast"|"lunch"|"snack"|"dinner";planningDate?:string;personIds?:string[];onVariantsChanged?:()=>void}) {
  const {locale} = useI18n(); const pt = locale === "pt-PT";
  const [rows, setRows] = useState<ReviewRecipe[]>([]); const [refs, setRefs] = useState<FodmapReference[]>([]);
  const [selected, setSelected] = useState(""); const [search, setSearch] = useState("");
  const [view, setView] = useState<"recipes" | "sources">("recipes");
  const [error, setError] = useState(""); const [loading, setLoading] = useState(true); const [revision, setRevision] = useState(0);
  const [retail, setRetail] = useState<RetailAlternative[]>([]);
  const [retailError, setRetailError] = useState("");
  useEffect(() => {
    let cancelled = false;
    void listRetailAlternatives(familyId).then(rows => {if (!cancelled) setRetail(rows);})
      .catch(e => {if (!cancelled) setRetailError(String(e));});
    return () => {cancelled = true;};
  }, [familyId]);
  useEffect(() => {
    let cancelled = false; setLoading(true); setError("");
    void Promise.all([listRecipeReviews(familyId), listFodmapReferences(familyId)]).then(([recipes, references]) => {
      if (!cancelled) {setRows(recipes); setRefs(references);}
    }).catch(e => {if (!cancelled) setError(String(e));}).finally(() => {if (!cancelled) setLoading(false);});
    return () => {cancelled = true;};
  }, [familyId, revision]);
  const scopedRows = recipeId ? rows.filter(r=>r.id===recipeId) : rows;
  const filtered = scopedRows.filter(r => r.name.toLocaleLowerCase(locale).includes(search.toLocaleLowerCase(locale)));
  const recipe = filtered.find(r => r.id === selected) ?? filtered[0]; const counts = reviewCounts(scopedRows);
  const refById = new Map(refs.map(r => [r.id, r]));
  const labels = pt ? {high: "Orientação geral: maior teor", low: "Orientação geral: menor teor", variable: "Variável", unknown: "Desconhecido"}
    : {high: "General guidance: higher content", low: "General guidance: lower content", variable: "Variable", unknown: "Unknown"};
  return <section className="dietary-review" aria-busy={loading}>
    <header><h2>{pt ? "Substituições de ingredientes" : "Ingredient substitutions"}</h2>
      <p>{pt ? "Rever alternativas para cozinhar em família. As propostas não alteram as receitas, o plano semanal ou a lista de compras. A adequação depende dos produtos, preparação, quantidades e regras de cada pessoa." : "Review alternatives for family cooking. Proposals do not change recipes, the weekly plan or shopping list. Suitability depends on products, preparation, quantities and each person's rules."}</p>
      <p>{counts.recipes} {pt ? "receitas" : "recipes"} · {counts.proposals} {pt ? "propostas em revisão" : "proposals under review"} · {counts.missingIngredients} {pt ? "sem ingredientes" : "without ingredients"}</p>
      {!recipeId && <nav className="dietary-actions" aria-label={pt ? "Revisão alimentar" : "Dietary review"}>
        <button type="button" aria-pressed={view === "recipes"} onClick={() => setView("recipes")}>{pt ? "Receitas e alternativas" : "Recipes and alternatives"}</button>
        <button type="button" aria-pressed={view === "sources"} onClick={() => setView("sources")}>{pt ? "FODMAP · fontes e dados" : "FODMAP · sources and data"}</button>
      </nav>}
    </header>
    {error && <p role="alert">{error} <button type="button" onClick={() => setRevision(x => x + 1)}>{pt ? "Tentar novamente" : "Retry"}</button></p>}
    {retailError && <p role="status">{pt ? "Alternativas de supermercado indisponíveis: " : "Supermarket alternatives unavailable: "}{retailError}</p>}
    {loading && <p role="status">{pt ? "A carregar…" : "Loading…"}</p>}
    {!loading && view === "recipes" && <>
      {!recipeId && <label className="dietary-filter">{pt ? "Pesquisar receita" : "Search recipes"}<input type="search" value={search} onChange={e => setSearch(e.target.value)} /></label>}
      <div className={recipeId ? "" : "dietary-layout"}>{!recipeId && <nav className="dietary-recipe-list" aria-label={pt ? "Receitas" : "Recipes"}>
        {filtered.map(r => <button type="button" key={r.id} aria-current={recipe?.id === r.id ? "page" : undefined} onClick={() => setSelected(r.id)}>{r.name} · {r.ingredients.reduce((n,i) => n + i.substitutions.filter(s => s.status !== "rejected").length, 0)}</button>)}
        {!filtered.length && <p>{pt ? "Sem receitas correspondentes." : "No matching recipes."}</p>}
      </nav>}
      {!recipe && <p role="status">{pt ? "Receita selecionada indisponível para revisão." : "Selected recipe is unavailable for review."}</p>}
      {recipe && <article className="dietary-card" key={recipe.id}><h3>{recipe.name}</h3>
        <RecipeVariantEditor key={recipe.id} familyId={familyId} recipe={recipe} planningDate={planningDate} personIds={personIds} mealType={mealType} onChanged={()=>{void listRecipeReviews(familyId).then(setRows).catch(e=>setError(String(e)));onVariantsChanged?.();}}/>
        <p className="dietary-badge">{pt ? "Adequação FODMAP ainda não avaliada por porção" : "FODMAP suitability has not been assessed per serving"}</p>
        {!recipe.ingredients.length && <p>{pt ? "Composição em falta. Obter marca, rótulo e ingredientes antes de avaliar ou adaptar." : "Missing composition. Obtain brand, label and ingredients before assessing or adapting."}</p>}
        {recipe.ingredients.map(i => <div className="dietary-ingredient" key={i.id}>
          <h4><IngredientAlternativeLine name={i.name} quantity={`${new Intl.NumberFormat(locale, {maximumFractionDigits: 4}).format(Number(i.quantity))} ${i.unit}`} alternatives={[...new Set(i.substitutions.filter(s=>s.status!=="rejected").map(s=>s.replacement_name))]}/></h4>
          <p className="dietary-help">{pt ? "Quantidade da receita completa" : "Quantity for the whole recipe"}</p>
          {!i.references.length && <p>{pt ? "Sem referência associada — não significa baixo teor." : "No linked reference — this does not mean low content."}</p>}
          {i.references.map(ref => <p key={ref.id}><span className={`dietary-badge ${ref.classification}`}>{labels[ref.classification]}</span> <a href={ref.source_url} target="_blank" rel="noreferrer">{ref.source_name}</a> · {pt ? "Categoria geral; produto e dose por verificar." : "General category; product and dose unverified."}</p>)}
          {i.substitutions.map(s => <SubstitutionCard key={`${s.id}:${s.version}`} familyId={familyId} row={s} reference={s.reference_id ? refById.get(s.reference_id) : undefined} onChanged={() => setRevision(x => x + 1)} />)}
          <RetailAlternativeCards products={retail.filter(p => p.applicable_food_item_ids.includes(i.food_item_id))}/>
          <NewSubstitution key={`${i.id}:${revision}`} familyId={familyId} ingredient={i} references={refs} onChanged={() => setRevision(x => x + 1)} />
        </div>)}
      </article>}
      </div></>}
    {!loading && view === "sources" && <>
      <article className="dietary-card"><h3>Monash University</h3>
        <p>{pt ? "Seleção de resumos públicos com fonte e data, não a base laboratorial integral da aplicação. Não foram importados limites por porção nem concentrações." : "A selection of public summaries with source and date, not the app's full laboratory database. No serving limits or concentrations have been imported."}</p>
        <a href="https://www.monashfodmap.com/get-app-help/" target="_blank" rel="noreferrer">{pt ? "Base laboratorial e aplicação Monash" : "Monash laboratory database and app"}</a>
      </article>
      <article className="dietary-card"><h3>FODMAP Friendly</h3><p>{pt ? "Fonte adicional com testes laboratoriais. A base detalhada não foi importada; é necessário obter acesso e condições de utilização para a integrar." : "An additional laboratory testing source. Its detailed database has not been imported; access and usage terms are needed to integrate it."}</p><a href="https://fodmapfriendly.com/ingredient-testing/" target="_blank" rel="noreferrer">{pt ? "Método de testes" : "Testing method"}</a></article>
      <p>{refs.length} {pt ? "referências educativas importadas. Menor teor é uma orientação geral, não uma garantia para esta pessoa ou refeição." : "imported educational references. Lower content is general guidance, not a guarantee for this person or meal."}</p>
      {refs.map(ref => <article className="dietary-card dietary-source" key={ref.id}>
        <h3>{pt ? ref.name_pt : ref.name_en} <span className={`dietary-badge ${ref.classification}`}>{labels[ref.classification]}</span></h3>
        <p>{ref.fodmap_groups.join(", ")}</p><p>{pt ? ref.notes_pt : ref.notes_en}</p>
        <p><a href={ref.source_url} target="_blank" rel="noreferrer">{ref.source_name}</a> · {pt ? "Consultado em" : "Retrieved"} {ref.retrieved_on}</p>
      </article>)}
    </>}
  </section>;
}
