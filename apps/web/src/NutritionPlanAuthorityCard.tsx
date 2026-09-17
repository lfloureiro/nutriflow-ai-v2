import { useEffect, useState } from "react";

import {
  getNutritionPlanAuthorityOverview,
  type NutritionPlanAuthorityOverview,
} from "./api/nutritionPlanClient";
import type { NutritionPlanAuthorityState, NutritionPlanSummary } from "./api/planFitTypes";
import type { PlanningMealType } from "./api/types";
import { useI18n, type Locale } from "./i18n";
import "./nutrition-plan-authority.css";

const COPY = {
  "pt-PT": {
    eyebrow: "Autoridade nutricional",
    title: "Plano nutricional",
    active_plan: "Plano activo",
    partial_plan_coverage: "Cobertura parcial",
    no_active_plan: "Sem plano nutricional activo",
    plan_conflict: "Conflito no plano",
    activeHelp:
      "Existe orientação activa e aplicável às principais refeições. O NutriFlow pode usar esta evidência para avaliar alinhamento com o plano.",
    partialHelp:
      "Existe um plano activo, mas nem todas as refeições têm orientação aplicável. O NutriFlow só assume alinhamento quando a evidência devolvida pelo plano o suporta.",
    noneHelp:
      "As recomendações podem considerar segurança, preferências e contexto, mas não são apresentadas como optimizadas segundo um plano nutricional.",
    conflictHelp:
      "Existem regras obrigatórias em conflito. O NutriFlow não apresenta opções como alinhadas com o plano enquanto o conflito não for revisto.",
    source: "Origem",
    validity: "Validade",
    from: "desde",
    until: "até",
    openEnded: "sem data final",
    coverage: "Cobertura por refeição",
    breakfast: "Pequeno-almoço",
    lunch: "Almoço",
    snack: "Lanche",
    dinner: "Jantar",
    importPlan: "Importar plano",
    loading: "A verificar plano…",
    unavailable: "Não foi possível verificar o estado do plano.",
    retry: "Tentar novamente",
  },
  en: {
    eyebrow: "Nutrition authority",
    title: "Nutrition plan",
    active_plan: "Active plan",
    partial_plan_coverage: "Partial coverage",
    no_active_plan: "No active nutrition plan",
    plan_conflict: "Plan conflict",
    activeHelp:
      "Active guidance applies to the main meals. NutriFlow can use this evidence when assessing alignment with the plan.",
    partialHelp:
      "An active plan exists, but not every meal has applicable guidance. NutriFlow only claims alignment when returned plan evidence supports it.",
    noneHelp:
      "Recommendations can still consider safety, preferences and context, but are not presented as optimized to a nutrition plan.",
    conflictHelp:
      "Mandatory rules conflict. NutriFlow does not present options as aligned with the plan until the conflict is reviewed.",
    source: "Source",
    validity: "Validity",
    from: "from",
    until: "until",
    openEnded: "no end date",
    coverage: "Coverage by meal",
    breakfast: "Breakfast",
    lunch: "Lunch",
    snack: "Snack",
    dinner: "Dinner",
    importPlan: "Import plan",
    loading: "Checking plan…",
    unavailable: "Could not verify the plan state.",
    retry: "Try again",
  },
} as const;

function formatDate(value: string, locale: Locale): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function planSource(plan: NutritionPlanSummary): string {
  return plan.source_name ?? plan.source_type.replaceAll("_", " ");
}

function helpText(state: NutritionPlanAuthorityState, locale: Locale): string {
  const copy = COPY[locale];
  if (state === "active_plan") return copy.activeHelp;
  if (state === "partial_plan_coverage") return copy.partialHelp;
  if (state === "plan_conflict") return copy.conflictHelp;
  return copy.noneHelp;
}

function mealLabel(mealType: PlanningMealType, locale: Locale): string {
  return COPY[locale][mealType];
}

export default function NutritionPlanAuthorityCard({
  effectiveDate,
  onImportRequested,
  personId,
  revision = 0,
}: {
  effectiveDate: string;
  onImportRequested: () => void;
  personId: string;
  revision?: number;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [overview, setOverview] = useState<NutritionPlanAuthorityOverview | null>(null);
  const [error, setError] = useState(false);
  const [requestRevision, setRequestRevision] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError(false);
    void getNutritionPlanAuthorityOverview(personId, effectiveDate)
      .then((result) => {
        if (!cancelled) setOverview(result);
      })
      .catch(() => {
        if (!cancelled) {
          setOverview(null);
          setError(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [effectiveDate, personId, requestRevision, revision]);

  if (error) {
    return (
      <section className="nutrition-authority nutrition-authority--error">
        <div>
          <span className="eyebrow">{copy.eyebrow}</span>
          <h3>{copy.title}</h3>
          <p>{copy.unavailable}</p>
        </div>
        <button
          className="button ghost"
          onClick={() => setRequestRevision((current) => current + 1)}
          type="button"
        >
          {copy.retry}
        </button>
      </section>
    );
  }

  if (!overview) {
    return (
      <section className="nutrition-authority" aria-live="polite">
        <span className="eyebrow">{copy.eyebrow}</span>
        <span className="nutrition-authority__loading">{copy.loading}</span>
      </section>
    );
  }

  return (
    <section
      className={`nutrition-authority nutrition-authority--${overview.state}`}
      aria-labelledby="nutrition-authority-title"
    >
      <div className="nutrition-authority__header">
        <div>
          <span className="eyebrow">{copy.eyebrow}</span>
          <h3 id="nutrition-authority-title">{copy.title}</h3>
        </div>
        <span className="nutrition-authority__status">{copy[overview.state]}</span>
      </div>

      <p className="nutrition-authority__help">{helpText(overview.state, locale)}</p>

      {overview.active_plans.length > 0 ? (
        <div className="nutrition-authority__plans">
          {overview.active_plans.map((plan) => (
            <article className="nutrition-authority__plan" key={plan.id}>
              <strong>{plan.title}</strong>
              <dl>
                <div>
                  <dt>{copy.source}</dt>
                  <dd>{planSource(plan)}</dd>
                </div>
                <div>
                  <dt>{copy.validity}</dt>
                  <dd>
                    {copy.from} {formatDate(plan.valid_from, locale)}
                    {" · "}
                    {plan.valid_until
                      ? `${copy.until} ${formatDate(plan.valid_until, locale)}`
                      : copy.openEnded}
                  </dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      ) : null}

      <div className="nutrition-authority__coverage">
        <span>{copy.coverage}</span>
        <div>
          {overview.meals.map((meal) => (
            <span
              className={`nutrition-authority__meal nutrition-authority__meal--${meal.state}`}
              key={meal.meal_type}
              title={copy[meal.state]}
            >
              {mealLabel(meal.meal_type, locale)}
            </span>
          ))}
        </div>
      </div>

      {overview.state === "no_active_plan" || overview.state === "partial_plan_coverage" ? (
        <div className="nutrition-authority__actions">
          <button className="button primary" onClick={onImportRequested} type="button">
            {copy.importPlan}
          </button>
        </div>
      ) : null}
    </section>
  );
}
