import { useMemo, useState, type FormEvent } from "react";
import { createSubstitution, type ReviewRecipe } from "./api/dietaryReviewClient";
import { useI18n } from "./i18n";

/**
 * A live research backlog derived from persisted recipe ingredients and current
 * family exclusions. Adding a proposal persists it through the existing
 * recipe-adaptations API; nothing is marked safe, approved or applied.
 */
export function adaptationResearchItems(recipes: ReviewRecipe[], excluded: string[]) {
  const blocked = new Set(excluded);
  return recipes.flatMap(recipe =>
    recipe.ingredients
      .filter(ingredient => blocked.has(ingredient.food_item_id))
      .map(ingredient => {
        const proposals = ingredient.substitutions.filter(row => row.status !== "rejected");
        const hasVariant = Boolean(recipe.active_variants?.some(variant =>
          variant.operations.some(operation => operation.recipe_ingredient_id === ingredient.id)));
        return {
          key: `${recipe.id}:${ingredient.id}`,
          recipeId: recipe.id,
          recipeName: recipe.name,
          ingredientId: ingredient.id,
          ingredientName: ingredient.name,
          quantity: ingredient.quantity,
          unit: ingredient.unit,
          proposals,
          hasVariant,
          missing: proposals.length === 0 && !hasVariant,
        };
      }),
  );
}

function researchUrl(domain: string, ingredient: string) {
  return `https://www.google.com/search?q=${encodeURIComponent(
    `site:${domain} ${ingredient} alternativa low FODMAP ingredientes`,
  )}`;
}

export default function AdaptationResearchQueue({
  recipes, excluded, familyId, onChanged,
}: {
  recipes: ReviewRecipe[];
  excluded: string[];
  familyId: string;
  onChanged: () => void;
}) {
  const { locale } = useI18n();
  const pt = locale === "pt-PT";
  const items = useMemo(() => adaptationResearchItems(recipes, excluded), [recipes, excluded]);
  const missing = items.filter(item => item.missing).length;
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [replacement, setReplacement] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const selected = items.find(item => item.key === selectedId);

  async function propose(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected || !replacement.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      await createSubstitution(familyId, {
        recipe_ingredient_id: selected.ingredientId,
        replacement_name: replacement.trim(),
        notes: notes.trim() || (pt
          ? "Candidato para investigar; FODMAP, rótulo, dose e equivalência nutricional por validar."
          : "Research candidate; FODMAP, label, serving and nutritional equivalence unverified."),
        replacement_quantity: null,
        replacement_unit: null,
      });
      setReplacement("");
      setNotes("");
      setSelectedId(null);
      onChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <details className="nf-adaptation-research-queue">
      <summary>
        <span aria-hidden="true" className="nf-research-flag">!</span>
        {pt ? "Ingredientes para investigar e adaptar" : "Ingredients requiring research"}
        <strong>{items.length}</strong>
        <small>{missing} {pt ? "sem alternativa registada" : "without a recorded alternative"}</small>
      </summary>
      <p className="nf-research-explanation">
        {pt
          ? "Lista calculada a partir das exclusões e dos ingredientes das receitas da família. A ausência de uma troca não torna a receita compatível. As propostas ficam guardadas para revisão; não alteram refeições, receitas originais ou compras."
          : "Derived from family exclusions and recipe ingredients. Missing swaps never imply compatibility. Proposals are saved for review only; they do not change meals, original recipes or shopping."}
      </p>
      {!items.length ? (
        <p>{pt
          ? "Sem ingredientes associados às exclusões nesta consulta. Isso não equivale a validação FODMAP das restantes receitas."
          : "No ingredients matched the current exclusions. This does not certify FODMAP suitability of other recipes."}</p>
      ) : (
        <div className="nf-research-list">
          {items.map(item => (
            <article key={item.key} className={item.missing ? "is-missing" : "has-proposals"}>
              <div>
                <strong>{item.recipeName}</strong>
                <p>{item.ingredientName} · {item.quantity} {item.unit}</p>
                <small>{item.missing
                  ? (pt ? "Sem substituição — pesquisa necessária" : "No substitute — research needed")
                  : item.hasVariant
                    ? (pt ? "Variante existente — validar por pessoa e porção" : "Existing variant — verify for each person and serving")
                    : (pt ? `${item.proposals.length} proposta(s) por rever/aplicar` : `${item.proposals.length} proposal(s) awaiting review/application`)}</small>
              </div>
              <nav aria-label={pt ? `Investigar ${item.ingredientName}` : `Research ${item.ingredientName}`}>
                <a href={researchUrl("monashfodmap.com", item.ingredientName)} target="_blank" rel="noopener noreferrer">Monash</a>
                <a href={researchUrl("auchan.pt", item.ingredientName)} target="_blank" rel="noopener noreferrer">Auchan</a>
                <a href={researchUrl("continente.pt", item.ingredientName)} target="_blank" rel="noopener noreferrer">Continente</a>
                <button type="button" className="button ghost small" onClick={() => {
                  setError("");
                  setSelectedId(old => old === item.key ? null : item.key);
                  setReplacement("");
                  setNotes("");
                }}>{pt ? "Registar alternativa" : "Record alternative"}</button>
              </nav>
              {selectedId === item.key && selected && (
                <form onSubmit={event => void propose(event)} className="nf-research-proposal">
                  <label>{pt ? "Alternativa encontrada (nome concreto)" : "Researched alternative (specific name)"}
                    <input required maxLength={160} value={replacement} onChange={event => setReplacement(event.target.value)} />
                  </label>
                  <label>{pt ? "Fonte, ingredientes, dose e dúvidas" : "Source, ingredients, serving and uncertainties"}
                    <textarea maxLength={5000} value={notes} onChange={event => setNotes(event.target.value)} />
                  </label>
                  <p>{pt
                    ? "É apenas uma proposta para avaliação, sem aprovação automática."
                    : "This is a research proposal only, not automatic approval."}</p>
                  <button type="submit" className="button secondary small" disabled={busy || !replacement.trim()}>
                    {busy ? (pt ? "A guardar…" : "Saving…") : (pt ? "Guardar para revisão" : "Save for review")}
                  </button>
                  {error && <p role="alert">{error}</p>}
                </form>
              )}
            </article>
          ))}
        </div>
      )}
    </details>
  );
}
