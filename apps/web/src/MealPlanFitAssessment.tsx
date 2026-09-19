import type {
  MealPlanFitGuideline,
  MealPlanFitResult,
  MealPlanFitRule,
  NutritionPlanAuthorityState,
  PlanFitConflict,
} from "./api/planFitTypes";
import { useI18n, type Locale } from "./i18n";
import {
  formatPlanFitNumber,
  planFitConflictMessage,
  planFitGuidelineExplanation,
  planFitRuleExplanation,
  planFitSafetyIssue,
  planFitSourceLabel,
  planFitTargetLabel,
  planFitUnitLabel,
} from "./mealPlanFitPresentation";
import "./meal-plan-fit.css";

export type MealPlanFitAssessmentData = {
  eligible: boolean;
  status: MealPlanFitResult["status"];
  fitScore: string | null;
  authorityState: NutritionPlanAuthorityState;
  activePlanTitles: string[];
  nutrition: MealPlanFitResult["candidate"]["nutrition"];
  conflicts: PlanFitConflict[];
  safetyIssues: string[];
  ruleResults: MealPlanFitRule[];
  guidelineResults: MealPlanFitGuideline[];
};

export function assessmentDataFromResult(
  result: MealPlanFitResult,
): MealPlanFitAssessmentData {
  return {
    eligible: result.eligible,
    status: result.status,
    fitScore: result.fit_score,
    authorityState: result.nutrition_plan_authority.state,
    activePlanTitles: result.active_plans.map((plan) => plan.title),
    nutrition: result.candidate.nutrition,
    conflicts: result.conflicts,
    safetyIssues: result.safety_issues,
    ruleResults: result.rule_results,
    guidelineResults: result.guideline_results,
  };
}

const COPY = {
  "pt-PT": {
    score: "Adequação",
    eligible: "Elegível",
    blocked: "Bloqueada",
    planAuthority: "Estado do plano",
    active_plan: "Plano activo",
    partial_plan_coverage: "Cobertura parcial",
    no_active_plan: "Sem plano activo",
    plan_conflict: "Conflito no plano",
    nutrition: "Composição nutricional da porção",
    mealRules: "Regras desta refeição",
    dailyImpact: "Impacto nas metas do dia",
    guidelines: "Orientações do plano",
    safety: "Bloqueios de segurança",
    conflicts: "Conflitos no plano",
    pass: "Cumpre",
    partial: "Parcial",
    fail: "Falha",
    unknown: "Desconhecido",
    conflict: "Conflito",
    support: "Ajuda a cumprir",
    neutral: "Neutro",
    not_evaluated: "Ainda não avaliado",
    mandatory: "Obrigatória",
    advisory: "Recomendação",
    observed: "Observado",
    projected: "Total diário projetado",
    target: "Alvo",
    guidanceHelp:
      "As orientações sem evidência estruturada suficiente permanecem visíveis, mas não são tratadas como se tivessem sido automaticamente verificadas.",
  },
  en: {
    score: "Fit",
    eligible: "Eligible",
    blocked: "Blocked",
    planAuthority: "Plan state",
    active_plan: "Active plan",
    partial_plan_coverage: "Partial coverage",
    no_active_plan: "No active plan",
    plan_conflict: "Plan conflict",
    nutrition: "Nutrition in this portion",
    mealRules: "Rules for this meal",
    dailyImpact: "Impact on today's targets",
    guidelines: "Plan guidance",
    safety: "Safety blocks",
    conflicts: "Plan conflicts",
    pass: "Meets",
    partial: "Partial",
    fail: "Fails",
    unknown: "Unknown",
    conflict: "Conflict",
    support: "Supports",
    neutral: "Neutral",
    not_evaluated: "Not evaluated yet",
    mandatory: "Mandatory",
    advisory: "Advisory",
    observed: "Observed",
    projected: "Projected daily total",
    target: "Target",
    guidanceHelp:
      "Guidance without sufficient structured evidence remains visible but is not presented as automatically verified.",
  },
} as const;

function targetText(rule: MealPlanFitRule, locale: Locale): string {
  const unit = rule.target_unit ? ` ${planFitUnitLabel(rule.target_unit, locale)}` : "";
  if (rule.operator === "range" && rule.target_min !== null && rule.target_max !== null) {
    return `${formatPlanFitNumber(rule.target_min, locale)}–${formatPlanFitNumber(
      rule.target_max,
      locale,
    )}${unit}`;
  }
  if (["min", "gte", ">=", ">"].includes(rule.operator) && rule.target_min !== null) {
    return `≥ ${formatPlanFitNumber(rule.target_min, locale)}${unit}`;
  }
  if (["max", "lte", "<=", "<"].includes(rule.operator) && rule.target_max !== null) {
    return `≤ ${formatPlanFitNumber(rule.target_max, locale)}${unit}`;
  }
  if (rule.target_value !== null) {
    return `${formatPlanFitNumber(rule.target_value, locale)}${unit}`;
  }
  if (rule.operator === "exclude") {
    return locale === "pt-PT" ? "Excluir" : "Exclude";
  }
  return rule.operator;
}

function fitPercent(value: string | null): string {
  if (value === null) return "—";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  return `${Math.round(numeric * 100)}%`;
}

function nutrientRows(
  nutrition: MealPlanFitAssessmentData["nutrition"],
  locale: Locale,
) {
  const rows = Object.entries(nutrition.nutrients).map(([key, nutrient]) => ({
    key,
    label: planFitTargetLabel(key, locale),
    value: `${formatPlanFitNumber(nutrient.value, locale)} ${planFitUnitLabel(
      nutrient.unit,
      locale,
      nutrient.value,
    )}`.trim(),
  }));
  rows.sort((left, right) => left.label.localeCompare(right.label, locale));
  if (nutrition.energy_kcal !== null) {
    rows.unshift({
      key: "energy_kcal",
      label: planFitTargetLabel("energy_kcal", locale),
      value: `${formatPlanFitNumber(nutrition.energy_kcal, locale)} kcal`,
    });
  }
  return rows;
}

export default function MealPlanFitAssessment({
  data,
  compact = false,
}: {
  data: MealPlanFitAssessmentData;
  compact?: boolean;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const mealRules = data.ruleResults.filter((rule) => rule.scope !== "daily");
  const dailyRules = data.ruleResults.filter((rule) => rule.scope === "daily");
  const nutrition = nutrientRows(data.nutrition, locale);
  const score = fitPercent(data.fitScore);

  function renderRule(rule: MealPlanFitRule) {
    return (
      <article className="plan-fit-rule" key={rule.rule_id}>
        <div className="plan-fit-rule__header">
          <div>
            <strong>{planFitTargetLabel(rule.target_key, locale)}</strong>
            <small>
              {planFitSourceLabel(
                rule.source.plan_title ?? rule.source.source_name ?? rule.source.rule_source,
                locale,
              )}
            </small>
          </div>
          <span className={`plan-fit-status status-${rule.status}`}>
            {copy[rule.status]}
          </span>
        </div>
        <div className="plan-fit-rule__values">
          <span>{rule.is_mandatory ? copy.mandatory : copy.advisory}</span>
          <span>
            {copy.target}: {targetText(rule, locale)}
          </span>
          {rule.observed_value !== null ? (
            <span>
              {copy.observed}: {formatPlanFitNumber(rule.observed_value, locale)}{" "}
              {planFitUnitLabel(rule.observed_unit, locale, rule.observed_value)}
            </span>
          ) : null}
          {rule.projected_daily_value !== null ? (
            <span>
              {copy.projected}: {formatPlanFitNumber(rule.projected_daily_value, locale)}{" "}
              {planFitUnitLabel(rule.target_unit, locale, rule.projected_daily_value)}
            </span>
          ) : null}
        </div>
        <p>{planFitRuleExplanation(rule, locale)}</p>
      </article>
    );
  }

  return (
    <div className={`plan-fit-result ${compact ? "plan-fit-result--compact" : ""}`}>
      <div className="plan-fit-summary">
        <div>
          <span>{copy.score}</span>
          <strong>{score}</strong>
        </div>
        <div>
          <span>{data.eligible ? copy.eligible : copy.blocked}</span>
          <strong className={`plan-fit-status status-${data.status}`}>
            {copy[data.status]}
          </strong>
        </div>
        <div className="plan-fit-summary__plans">
          <span>{copy.planAuthority}</span>
          <strong>
            {copy[data.authorityState]}
            {data.activePlanTitles.length > 0
              ? ` · ${data.activePlanTitles.join(" · ")}`
              : ""}
          </strong>
        </div>
      </div>

      {nutrition.length > 0 ? (
        <section className="plan-fit-nutrition">
          <h4>{copy.nutrition}</h4>
          <dl>
            {nutrition.map((row) => (
              <div key={row.key}>
                <dt>{row.label}</dt>
                <dd>{row.value}</dd>
              </div>
            ))}
          </dl>
        </section>
      ) : null}

      {data.safetyIssues.length > 0 ? (
        <div className="plan-fit-alert">
          <strong>{copy.safety}</strong>
          {data.safetyIssues.map((issue, index) => (
            <span key={`${issue}:${index}`}>{planFitSafetyIssue(issue, locale)}</span>
          ))}
        </div>
      ) : null}

      {data.conflicts.length > 0 ? (
        <div className="plan-fit-alert">
          <strong>{copy.conflicts}</strong>
          {data.conflicts.map((item) => (
            <span key={item.rule_ids.join(":")}>{planFitConflictMessage(item, locale)}</span>
          ))}
        </div>
      ) : null}

      {mealRules.length > 0 ? (
        <section className="plan-fit-rules">
          <h4>{copy.mealRules}</h4>
          {mealRules.map(renderRule)}
        </section>
      ) : null}

      {dailyRules.length > 0 ? (
        <section className="plan-fit-rules">
          <h4>{copy.dailyImpact}</h4>
          {dailyRules.map(renderRule)}
        </section>
      ) : null}

      {data.guidelineResults.length > 0 ? (
        <details className="plan-fit-guidelines" open={!compact}>
          <summary>
            {copy.guidelines} ({data.guidelineResults.length})
          </summary>
          <p className="muted compact">{copy.guidanceHelp}</p>
          <div className="plan-fit-rules">
            {data.guidelineResults.map((guideline) => (
              <article className="plan-fit-rule" key={guideline.guideline_id}>
                <div className="plan-fit-rule__header">
                  <div>
                    <strong>{guideline.description}</strong>
                    <small>
                      {planFitSourceLabel(
                        guideline.source.plan_title ??
                          guideline.source.source_name ??
                          guideline.source.rule_source,
                        locale,
                      )}
                    </small>
                  </div>
                  <span className={`plan-fit-status status-${guideline.status}`}>
                    {copy[guideline.status]}
                  </span>
                </div>
                <div className="plan-fit-rule__values">
                  <span>{guideline.is_mandatory ? copy.mandatory : copy.advisory}</span>
                </div>
                <p>{planFitGuidelineExplanation(guideline, locale)}</p>
              </article>
            ))}
          </div>
        </details>
      ) : null}
    </div>
  );
}
