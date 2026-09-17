import { useEffect, useMemo, useState } from "react";

import { ApiError } from "./api/client";
import {
  activateImportedNutritionPlan,
  applyNutritionPlanImport,
  createNutritionPlanImport,
  setNutritionPlanImportProposalStatus,
} from "./api/nutritionPlanImportClient";
import type {
  NutritionPlanImportCreate,
  NutritionPlanImportProposal,
  NutritionPlanImportSession,
} from "./api/nutritionPlanImportTypes";
import { useI18n } from "./i18n";
import { formatPlanFitNumber, planFitTargetLabel } from "./mealPlanFitPresentation";
import NutritionPlanDocumentPicker from "./NutritionPlanDocumentPicker";
import "./nutrition-plan-import.css";

const COPY = {
  "pt-PT": {
    title: "Plano do nutricionista",
    help: "Importa recomendações de um documento ou texto, revê a interpretação e só depois as adiciona ao plano.",
    open: "Importar recomendações",
    close: "Fechar",
    planTitle: "Nome do plano",
    sourceName: "Nutricionista / profissional",
    reference: "Referência (opcional)",
    validFrom: "Válido desde",
    text: "Recomendações",
    textHint: "Podes corrigir o texto extraído antes de o interpretar. A fonte original continua identificada pela referência do ficheiro.",
    ai: "Interpretar com IA",
    deterministic: "Analisar sem IA",
    aiHint: "A IA apenas propõe uma estrutura. Nada é ativado sem a tua confirmação explícita.",
    interpreting: "A interpretar…",
    review: "Rever propostas",
    confirmed: "Confirmada",
    rejected: "Rejeitada",
    proposed: "Por rever",
    confirm: "Confirmar",
    reject: "Rejeitar",
    source: "Texto de origem",
    confidence: "Confiança",
    mandatory: "Obrigatória",
    advisory: "Recomendação",
    unclassified: "Interpretação incerta — rejeita ou revê manualmente antes de aplicar.",
    apply: "Adicionar ao plano em rascunho",
    applying: "A adicionar…",
    activate: "Ativar plano",
    activating: "A ativar…",
    applied: "Recomendações adicionadas. O plano continua em rascunho até ser ativado.",
    active: "Plano ativo. As recomendações confirmadas já podem ser usadas pelo Plan-Fit.",
    incomplete: "Revê todas as propostas antes de aplicar.",
    needOne: "É necessário confirmar pelo menos uma proposta.",
    genericError: "Não foi possível concluir a importação.",
    aiUnavailable: "A interpretação por IA não está configurada neste ambiente. Podes usar a análise sem IA.",
    breakfast: "pequeno-almoço",
    lunch: "almoço",
    snack: "lanche",
    dinner: "jantar",
    numeric_rule: "Regra quantitativa",
    qualitative_guideline: "Orientação qualitativa",
    frequency_guideline: "Frequência",
    unclassifiedType: "Por classificar",
  },
  en: {
    title: "Nutritionist plan",
    help: "Import recommendations from a document or text, review the interpretation, then add them to the plan.",
    open: "Import recommendations",
    close: "Close",
    planTitle: "Plan name",
    sourceName: "Nutritionist / professional",
    reference: "Reference (optional)",
    validFrom: "Valid from",
    text: "Recommendations",
    textHint: "You can correct extracted text before interpreting it. The source file remains identified by the reference field.",
    ai: "Interpret with AI",
    deterministic: "Analyse without AI",
    aiHint: "AI only proposes structure. Nothing is activated without explicit confirmation.",
    interpreting: "Interpreting…",
    review: "Review proposals",
    confirmed: "Confirmed",
    rejected: "Rejected",
    proposed: "Needs review",
    confirm: "Confirm",
    reject: "Reject",
    source: "Source text",
    confidence: "Confidence",
    mandatory: "Mandatory",
    advisory: "Advisory",
    unclassified: "Uncertain interpretation — reject or edit manually before applying.",
    apply: "Add to draft plan",
    applying: "Adding…",
    activate: "Activate plan",
    activating: "Activating…",
    applied: "Recommendations added. The plan remains draft until activated.",
    active: "Plan active. Confirmed recommendations can now be used by Plan-Fit.",
    incomplete: "Review every proposal before applying.",
    needOne: "At least one proposal must be confirmed.",
    genericError: "Could not complete the import.",
    aiUnavailable: "AI interpretation is not configured in this environment. You can use non-AI analysis.",
    breakfast: "breakfast",
    lunch: "lunch",
    snack: "snack",
    dinner: "dinner",
    numeric_rule: "Numeric rule",
    qualitative_guideline: "Qualitative guidance",
    frequency_guideline: "Frequency",
    unclassifiedType: "Unclassified",
  },
} as const;

function errorText(error: unknown, fallback: string, aiUnavailable: string): string {
  if (error instanceof ApiError) {
    if (error.status === 503 && error.message.includes("OPENAI_API_KEY")) return aiUnavailable;
    return `${error.message} (HTTP ${error.status})`;
  }
  if (error instanceof Error) return error.message;
  return fallback;
}

function humanize(value: string | null): string {
  if (!value) return "—";
  return value.replaceAll("_", " ").replace(/^./, (char) => char.toUpperCase());
}

function proposalMeaning(
  proposal: NutritionPlanImportProposal,
  locale: "pt-PT" | "en",
): string {
  if (proposal.proposal_type === "unclassified") return humanize(proposal.description);
  if (proposal.proposal_type === "qualitative_guideline") return proposal.description ?? proposal.source_statement;
  if (proposal.proposal_type === "frequency_guideline") {
    const target = humanize(proposal.target_key);
    const minimum = proposal.minimum_occurrences;
    const maximum = proposal.maximum_occurrences;
    const count = minimum !== null ? `≥ ${minimum}` : maximum !== null ? `≤ ${maximum}` : "";
    return `${target} ${count} / ${locale === "pt-PT" ? "semana" : "week"}`.trim();
  }

  const target = proposal.target_key
    ? planFitTargetLabel(proposal.target_key, locale)
    : humanize(proposal.target_key);
  const unit = proposal.unit ? ` ${proposal.unit}` : "";
  let value = "";
  if (proposal.operator === "range" && proposal.value_min !== null && proposal.value_max !== null) {
    value = `${formatPlanFitNumber(proposal.value_min, locale)}–${formatPlanFitNumber(proposal.value_max, locale)}${unit}`;
  } else if (proposal.operator === "min" && proposal.value_min !== null) {
    value = `≥ ${formatPlanFitNumber(proposal.value_min, locale)}${unit}`;
  } else if (proposal.operator === "max" && proposal.value_max !== null) {
    value = `≤ ${formatPlanFitNumber(proposal.value_max, locale)}${unit}`;
  } else if (proposal.value_target !== null) {
    value = `${formatPlanFitNumber(proposal.value_target, locale)}${unit}`;
  }
  const meal = proposal.meal_type ? ` · ${COPY[locale][proposal.meal_type]}` : "";
  return `${target} ${value}${meal}`.trim();
}

export default function NutritionPlanImportPanel({
  onPlanActivated,
  openRequestToken = 0,
  personId,
  planningDate,
}: {
  onPlanActivated?: () => void;
  openRequestToken?: number;
  personId: string;
  planningDate: string;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [activating, setActivating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<NutritionPlanImportSession | null>(null);
  const [title, setTitle] = useState(locale === "pt-PT" ? "Plano do nutricionista" : "Nutritionist plan");
  const [sourceName, setSourceName] = useState("");
  const [sourceReference, setSourceReference] = useState("");
  const [sourceText, setSourceText] = useState("");
  const [validFrom, setValidFrom] = useState(planningDate);

  useEffect(() => {
    if (openRequestToken <= 0) return;
    setOpen(true);
    window.requestAnimationFrame(() => {
      document
        .getElementById("nutrition-import-title")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [openRequestToken]);

  const pending = session?.proposals.some((item) => item.confirmation_status === "proposed") ?? true;
  const confirmedCount = session?.proposals.filter((item) => item.confirmation_status === "confirmed").length ?? 0;
  const canApply = session?.status === "review" && !pending && confirmedCount > 0;

  const payload = useMemo<NutritionPlanImportCreate>(() => ({
    title: title.trim(),
    source_type: "nutritionist",
    source_name: sourceName.trim() || null,
    source_reference: sourceReference.trim() || null,
    source_text: sourceText.trim(),
    valid_from: validFrom,
    valid_until: null,
  }), [sourceName, sourceReference, sourceText, title, validFrom]);

  async function interpret(mode: "ai" | "deterministic") {
    if (!payload.title || !payload.source_text || !payload.valid_from) return;
    setBusy(true);
    setError(null);
    try {
      setSession(await createNutritionPlanImport(personId, payload, mode));
    } catch (caught: unknown) {
      setError(errorText(caught, copy.genericError, copy.aiUnavailable));
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(proposal: NutritionPlanImportProposal, status: "confirmed" | "rejected") {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await setNutritionPlanImportProposalStatus(
        personId,
        session.id,
        proposal.id,
        status,
      );
      setSession({
        ...session,
        proposals: session.proposals.map((item) => item.id === updated.id ? updated : item),
      });
    } catch (caught: unknown) {
      setError(errorText(caught, copy.genericError, copy.aiUnavailable));
    } finally {
      setBusy(false);
    }
  }

  async function apply() {
    if (!session || !canApply) return;
    setBusy(true);
    setError(null);
    try {
      setSession(await applyNutritionPlanImport(personId, session.id));
    } catch (caught: unknown) {
      setError(errorText(caught, copy.genericError, copy.aiUnavailable));
    } finally {
      setBusy(false);
    }
  }

  async function activate() {
    if (!session || session.status !== "applied") return;
    setActivating(true);
    setError(null);
    try {
      await activateImportedNutritionPlan(personId, session.nutrition_plan_id);
      setSession({
        ...session,
        nutrition_plan: { ...session.nutrition_plan, status: "active" },
      });
      onPlanActivated?.();
    } catch (caught: unknown) {
      setError(errorText(caught, copy.genericError, copy.aiUnavailable));
    } finally {
      setActivating(false);
    }
  }

  return (
    <section className="nutrition-import" aria-labelledby="nutrition-import-title">
      <div className="nutrition-import__header">
        <div>
          <h3 id="nutrition-import-title">{copy.title}</h3>
          <p>{copy.help}</p>
        </div>
        <button className="button ghost" type="button" onClick={() => setOpen((value) => !value)}>
          {open ? copy.close : copy.open}
        </button>
      </div>

      {open && session === null ? (
        <div className="nutrition-import__form">
          <div className="nutrition-import__row">
            <label className="field">
              <span>{copy.planTitle}</span>
              <input value={title} onChange={(event) => setTitle(event.target.value)} />
            </label>
            <label className="field">
              <span>{copy.sourceName}</span>
              <input value={sourceName} onChange={(event) => setSourceName(event.target.value)} />
            </label>
          </div>
          <div className="nutrition-import__row">
            <label className="field">
              <span>{copy.reference}</span>
              <input value={sourceReference} onChange={(event) => setSourceReference(event.target.value)} />
            </label>
            <label className="field">
              <span>{copy.validFrom}</span>
              <input type="date" value={validFrom} onChange={(event) => setValidFrom(event.target.value)} />
            </label>
          </div>
          <NutritionPlanDocumentPicker
            personId={personId}
            onExtracted={(extracted) => {
              setSourceText(extracted.source_text);
              if (!sourceReference.trim()) setSourceReference(extracted.filename);
            }}
          />
          <label className="field">
            <span>{copy.text}</span>
            <textarea value={sourceText} onChange={(event) => setSourceText(event.target.value)} />
            <small className="nutrition-import__hint">{copy.textHint}</small>
          </label>
          <div className="nutrition-import__actions">
            <button className="button primary" disabled={busy || !payload.title || !payload.source_text} onClick={() => void interpret("ai")} type="button">
              {busy ? copy.interpreting : copy.ai}
            </button>
            <button className="button ghost" disabled={busy || !payload.title || !payload.source_text} onClick={() => void interpret("deterministic")} type="button">
              {copy.deterministic}
            </button>
          </div>
          <small className="nutrition-import__hint">{copy.aiHint}</small>
        </div>
      ) : null}

      {error ? <div className="error-banner" role="alert"><span>{error}</span></div> : null}

      {open && session ? (
        <div className="nutrition-import__review">
          <h4>{copy.review}</h4>
          <p className="nutrition-import__summary">{session.parse_summary}</p>
          <div className="nutrition-import__proposals">
            {session.proposals.map((proposal) => (
              <article className="nutrition-import__proposal" key={proposal.id}>
                <div className="nutrition-import__proposal-header">
                  <div>
                    <strong>{proposalMeaning(proposal, locale)}</strong>
                    <div className="nutrition-import__meta">
                      {proposal.proposal_type === "unclassified"
                        ? copy.unclassifiedType
                        : copy[proposal.proposal_type]}
                      {` · ${proposal.is_mandatory ? copy.mandatory : copy.advisory}`}
                      {` · ${copy.confidence} ${Math.round(Number(proposal.confidence) * 100)}%`}
                    </div>
                  </div>
                  <span className={`nutrition-import__status ${proposal.confirmation_status}`}>
                    {copy[proposal.confirmation_status]}
                  </span>
                </div>
                <p className="nutrition-import__source"><strong>{copy.source}:</strong> “{proposal.source_statement}”</p>
                {proposal.proposal_type === "unclassified" ? <p>{copy.unclassified}</p> : null}
                {proposal.confirmation_status === "proposed" ? (
                  <div className="nutrition-import__review-actions">
                    {proposal.proposal_type !== "unclassified" ? (
                      <button className="button primary" disabled={busy} onClick={() => void setStatus(proposal, "confirmed")} type="button">
                        {copy.confirm}
                      </button>
                    ) : null}
                    <button className="button ghost" disabled={busy} onClick={() => void setStatus(proposal, "rejected")} type="button">
                      {copy.reject}
                    </button>
                  </div>
                ) : null}
              </article>
            ))}
          </div>

          <div className="nutrition-import__footer">
            <span className="nutrition-import__hint">
              {session.status === "review"
                ? pending ? copy.incomplete : confirmedCount === 0 ? copy.needOne : copy.aiHint
                : session.nutrition_plan.status === "active" ? copy.active : copy.applied}
            </span>
            {session.status === "review" ? (
              <button className="button primary" disabled={busy || !canApply} onClick={() => void apply()} type="button">
                {busy ? copy.applying : copy.apply}
              </button>
            ) : session.nutrition_plan.status !== "active" ? (
              <button className="button primary" disabled={activating} onClick={() => void activate()} type="button">
                {activating ? copy.activating : copy.activate}
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  );
}
