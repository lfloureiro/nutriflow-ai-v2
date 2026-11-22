import { useEffect, useMemo, useState } from "react";
import AdaptationResearchQueue, { adaptationResearchItems, buildAdaptationResearchBrief } from "./AdaptationResearchQueue";
import { createSubstitution, listRecipeReviews, type ReviewRecipe } from "./api/dietaryReviewClient";
import { getPlanningRestrictions, getWeekSetup } from "./api/planningWorkspaceClient";
import { buildAIResearchExport, previewAIResearchImport, type AIResearchPreviewRow } from "./aiResearchImport";
import { useI18n } from "./i18n";
import "./planning-journey.css";
import "./ai-workspace.css";

function currentMonday(): string {
  const local = new Date();
  const day = new Date(Date.UTC(local.getFullYear(), local.getMonth(), local.getDate(), 12));
  day.setUTCDate(day.getUTCDate() - ((day.getUTCDay() + 6) % 7));
  return day.toISOString().slice(0, 10);
}

export default function AIWorkspace({ familyId, onOpenPlanning }: {
  familyId: string;
  onOpenPlanning: () => void;
}) {
  const { locale } = useI18n();
  const pt = locale === "pt-PT";
  const [recipes, setRecipes] = useState<ReviewRecipe[]>([]);
  const [excluded, setExcluded] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [json, setJson] = useState("");
  const [preview, setPreview] = useState<AIResearchPreviewRow[] | null>(null);
  const [working, setWorking] = useState<string | null>(null);
  const [applied, setApplied] = useState<string[]>([]);

  async function reload() {
    const catalogue = await listRecipeReviews(familyId);
    setRecipes(catalogue);
  }

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    setPreview(null);
    const load = async () => {
      const catalogue = await listRecipeReviews(familyId);
      const monday = currentMonday();
      const nextMonday = new Date(`${monday}T12:00:00Z`);
      nextMonday.setUTCDate(nextMonday.getUTCDate() + 7);
      // The AI lab is generally opened from "prepare next week". Match
      // the most recently configured future week before falling back to
      // the current one, so the review queue uses the same exclusions.
      const futureSetup = await getWeekSetup(
        familyId, nextMonday.toISOString().slice(0, 10),
      ).catch(() => null);
      const setup = futureSetup ??
        await getWeekSetup(familyId, monday).catch(() => null);
      const automatic = setup
        ? await getPlanningRestrictions(familyId, setup).catch(() => null)
        : null;
      if (cancelled) return;
      setRecipes(catalogue);
      setExcluded([...new Set([
        ...(setup?.excluded_food_item_ids ?? []),
        ...(automatic?.excluded_food_item_ids ?? []),
      ])]);
      if (!setup || !automatic) setNotice(pt
        ? "As restrições não foram totalmente carregadas para a semana planeada. A lista pode estar incompleta."
        : "Planned-week restrictions were not fully loaded. The list may be incomplete.");
      setLoading(false);
    };
    void load().catch(e => {
      if (!cancelled) { setError(String(e)); setLoading(false); }
    });
    return () => { cancelled = true; };
  }, [familyId, pt]);

  const items = useMemo(() => adaptationResearchItems(recipes, excluded), [recipes, excluded]);
  const missing = items.filter(item => item.missing).length;
  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setNotice(pt ? "Pedido copiado. Envia-o à IA e pede o resultado JSON v1." : "Prompt copied. Ask the AI for v1 JSON output.");
    } catch { setNotice(pt ? "Área de transferência indisponível." : "Clipboard unavailable."); }
  }
  async function applyOne(row: AIResearchPreviewRow, index: number) {
    if (row.issue || working) return;
    const key = `${index}:${row.ingredient_id}`;
    setWorking(key);
    setError("");
    try {
      const latest = await listRecipeReviews(familyId);
      const original = latest.find(recipe => recipe.id === row.recipe_id)?.ingredients.find(
        ingredient => ingredient.id === row.ingredient_id);
      if (!original) throw Error("O ingrediente mudou ou foi eliminado. Importação cancelada.");
      if (original.substitutions.some(s => s.status !== "rejected" &&
        s.replacement_name.trim().toLocaleLowerCase() === row.replacement_name.toLocaleLowerCase())) {
        throw Error("Esta substituição já foi registada. Importação cancelada.");
      }
      await createSubstitution(familyId, {
        recipe_ingredient_id: row.ingredient_id,
        replacement_name: row.replacement_name,
        notes: [
          row.notes,
          `Fonte de investigação: ${row.evidence_url}`,
          row.retailer_url ? `Fonte comercial: ${row.retailer_url}` : "",
          "Importado como proposta NÃO VALIDADA; rótulo, FODMAP, dose, nutrição e participante por rever.",
        ].filter(Boolean).join("\n"),
        ...(row.proposed_quantity && row.proposed_unit ? {
          replacement_quantity: row.proposed_quantity,
          replacement_unit: row.proposed_unit,
        } : {}),
      });
      setApplied(previous => [...previous, key]);
      await reload();
      setNotice(pt ? "Proposta guardada para revisão; não foi aplicada à receita." : "Proposal saved for review only; the recipe is unchanged.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setWorking(null); }
  }

  return (
    <section className="nf-ai-workspace">
      <header className="screen-header">
        <div><span className="eyebrow">{pt ? "Inteligência à mesa" : "Intelligence at the table"}</span>
          <h1>{pt ? "Laboratório de receitas e ingredientes" : "Recipes and ingredients lab"}</h1>
          <p>{pt
            ? "Investiga, compara evidências e prepara adaptações. Nada entra automaticamente nas receitas, restrições ou compras."
            : "Research, compare evidence and prepare adaptations. Nothing automatically changes recipes, dietary restrictions or shopping."}</p>
        </div>
        <button type="button" className="button secondary" onClick={onOpenPlanning}>
          {pt ? "Abrir planeamento semanal" : "Open weekly planning"}
        </button>
      </header>
      {loading && <p role="status">{pt ? "A carregar receitas e restrições…" : "Loading recipes and restrictions…"}</p>}
      {error && <p role="alert" className="error-banner">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      {!loading && (
        <>
          <div className="nf-ai-metrics">
            <div><strong>{recipes.length}</strong><span>{pt ? "receitas em análise" : "recipes under review"}</span></div>
            <div><strong>{items.length}</strong><span>{pt ? "ocorrências para investigar" : "ingredient occurrences"}</span></div>
            <div><strong>{missing}</strong><span>{pt ? "sem proposta registada" : "without a proposal"}</span></div>
          </div>
          <section className="nf-ai-panel">
            <h2>{pt ? "Preparar pedido à IA" : "Prepare AI research request"}</h2>
            <p>{pt
              ? "O pedido estruturado inclui identificadores reais das receitas e dos ingredientes, propostas já registadas e um formato de resposta que a app consegue interpretar."
              : "The structured request contains real recipe and ingredient IDs, existing proposals and a response format the app can parse."}</p>
            <div className="nf-ai-actions">
              <button className="button primary" type="button" onClick={() => void copy(buildAIResearchExport(recipes, excluded))}>
                {pt ? "Copiar pedido JSON para IA" : "Copy JSON prompt for AI"}
              </button>
              <button className="button secondary" type="button" onClick={() => void copy(buildAdaptationResearchBrief(items))}>
                {pt ? "Copiar pedido em texto" : "Copy plain-text research brief"}
              </button>
            </div>
          </section>
          <section className="nf-ai-panel">
            <h2>{pt ? "Importar propostas da IA" : "Import AI research proposals"}</h2>
            <p>{pt
              ? "Cola o JSON gerado pela IA. Só são aceites IDs de ingredientes desta família, fontes HTTPS e o estado «unverified». O ficheiro é analisado localmente; cada proposta requer confirmação individual."
              : "Paste AI-generated JSON. Only this family's ingredient IDs, HTTPS sources and unverified status are accepted. Each proposal needs individual confirmation."}</p>
            <label htmlFor="nf-ai-json">{pt ? "Resposta JSON v1" : "JSON v1 response"}</label>
            <textarea id="nf-ai-json" rows={6} value={json} onChange={event => {
              setJson(event.target.value); setPreview(null); setApplied([]);
            }} placeholder={'{"schema_version":"nutriflow.ai-review.v1","suggestions":[]}'} />
            <button type="button" className="button secondary" disabled={!json.trim()} onClick={() => {
              try { setPreview(previewAIResearchImport(json, recipes)); setError(""); }
              catch (reason) { setPreview(null); setError(reason instanceof Error ? reason.message : String(reason)); }
            }}>{pt ? "Validar e pré-visualizar" : "Validate and preview"}</button>
            {preview && <div className="nf-ai-import-preview">
              <strong>{preview.length} {pt ? "propostas no ficheiro" : "proposals in file"}</strong>
              {preview.map((row, index) => {
                const key = `${index}:${row.ingredient_id}`;
                const done = applied.includes(key);
                return <article key={key}>
                  <strong>{row.recipeName}: {row.ingredientName} → {row.replacement_name}</strong>
                  <p>{row.notes}</p>
                  <small>{row.evidence_status} · <a target="_blank" rel="noopener noreferrer" href={row.evidence_url}>Fonte</a>
                    {row.retailer_url && <> · <a target="_blank" rel="noopener noreferrer" href={row.retailer_url}>Produto</a></>}</small>
                  {row.issue && <p role="status">{row.issue}</p>}
                  <button className="button secondary small" type="button"
                    disabled={!!row.issue || done || working !== null}
                    onClick={() => void applyOne(row, index)}>
                    {done ? (pt ? "Guardada para revisão" : "Saved for review")
                      : working === key ? (pt ? "A guardar…" : "Saving…")
                      : (pt ? "Guardar apenas esta proposta" : "Save only this proposal")}
                  </button>
                </article>;
              })}
            </div>}
          </section>
          <AdaptationResearchQueue recipes={recipes} excluded={excluded} familyId={familyId}
            onChanged={() => { void reload().catch(e => setError(String(e))); }} />
        </>
      )}
    </section>
  );
}
