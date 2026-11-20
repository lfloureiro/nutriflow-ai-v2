import { useEffect, useMemo, useRef, useState } from "react";

import { ApiError, listFamilyRecipes } from "./api/client";
import { proposeMealTransformations } from "./api/mealTransformationClient";
import type { MealTransformationResult } from "./api/mealTransformationTypes";
import { evaluateMealPlanFit } from "./api/planFitClient";
import type { MealPlanFitResult, MealPlanFitRule } from "./api/planFitTypes";
import type { Recipe } from "./api/recipeTypes";
import type { PlanningMealType } from "./api/types";
import { useI18n } from "./i18n";
import {
  formatPlanFitNumber,
  planFitConflictMessage,
  planFitCandidateNutrition,
  planFitMatchesRequest,
  planFitHasOpenEvidence,
  planFitEvidenceSource,
  planFitEvidenceSummary,
  planFitGuidelineExplanation,
  planFitRuleExplanation,
  planFitSafetyIssue,
  planFitSourceLabel,
  planFitTargetLabel,
  planFitUnitLabel,
} from "./mealPlanFitPresentation";

const MEAL_TYPES: PlanningMealType[] = ["breakfast", "lunch", "snack", "dinner"];

const COPY = {
  "pt-PT": {
    title: "Adequação ao plano",
    help: "Testa uma receita e uma porção contra as regras alimentares efetivas desta pessoa.",
    meal: "Refeição",
    recipe: "Receita",
    chooseActualRecipe: "Escolher receita e confirmar porção",
    quantity: "Quantidade",
    evaluate: "Avaliar",
    evaluating: "A avaliar…",
    improve: "Sugerir melhoria",
    improving: "A procurar melhorias…",
    improvementsTitle: "Melhorias estruturadas",
    improvementsHelp:
      "Só são mostradas substituições com evidência nutricional suficiente e melhoria mensurável no plano.",
    noImprovements: "Não foi encontrada uma substituição segura que melhore esta refeição.",
    replace: "Substituir",
    before: "Antes",
    after: "Depois",
    resolvesMandatory: "Resolve bloqueio obrigatório",
    changedRules: "Regras afetadas",
    noRecipes: "Não há receitas com composição nutricional para esta refeição.",
    noPlan: "Nenhum plano alimentar ativo; podem ainda existir metas ou limites gerais da pessoa.",
    planAuthority: "Estado do plano",
    active_plan: "Plano activo",
    partial_plan_coverage: "Cobertura parcial",
    no_active_plan: "Sem plano activo",
    plan_conflict: "Conflito no plano",
    score: "Adequação",
    portionNutrition: "Composição da porção avaliada",
    portionEnergy: "Energia da porção",
    portionUncertain: "Energia não disponível — não assumir zero.",
    nutrientUncertain: "Outros nutrientes sem evidência não são apresentados como zero.",
    coverageTitle: "Cobertura da avaliação",
    coverageRules: "Regras avaliadas",
    coverageUnknown: "Regras sem evidência suficiente",
    coverageGuidelines: "Orientações não avaliadas",
    coverageBlocks: "Bloqueios obrigatórios identificados",
    coverageHelp: "A falta de dados não demonstra segurança ou adequação nutricional. O resultado depende da porção indicada e das fontes efetivamente registadas.",
    provisionalScore: "Avaliação com evidência incompleta ou não confirmada. A pontuação não equivale a uma certificação nutricional ou FODMAP.",
    evidenceSource: "Origem registada",
    missingSource: "Origem não indicada",
    eligible: "Elegível",
    blocked: "Bloqueada",
    mealRules: "Regras desta refeição",
    dailyImpact: "Impacto nas metas do dia",
    guidelines: "Orientações não pontuadas",
    safety: "Bloqueios de segurança",
    conflicts: "Conflitos no plano",
    pass: "Cumpre",
    partial: "Parcial",
    fail: "Falha",
    unknown: "Desconhecido",
    conflict: "Conflito",
    support: "Ajuda a cumprir",
    not_evaluated: "Ainda não avaliado",
    mandatory: "Obrigatória",
    advisory: "Recomendação",
    observed: "Observado",
    projected: "Total diário projetado",
    target: "Alvo",
    breakfast: "Pequeno-almoço",
    lunch: "Almoço",
    snack: "Lanche",
    dinner: "Jantar",
    loadError: "Não foi possível carregar as receitas.",
    evaluateError: "Não foi possível avaliar esta refeição.",
    responseMismatch: "A avaliação recebida não corresponde à pessoa, data, refeição ou porção selecionada. Volta a avaliar.",
    transformationError: "Não foi possível calcular melhorias para esta refeição.",
  },
  en: {
    title: "Plan fit",
    help: "Test a recipe and portion against this person's effective nutrition guidance.",
    meal: "Meal",
    recipe: "Recipe",
    chooseActualRecipe: "Choose actual recipe and confirm portion",
    quantity: "Quantity",
    evaluate: "Evaluate",
    evaluating: "Evaluating…",
    improve: "Suggest improvement",
    improving: "Finding improvements…",
    improvementsTitle: "Structured improvements",
    improvementsHelp:
      "Only substitutions with sufficient nutrition evidence and measurable plan improvement are shown.",
    noImprovements: "No safe substitution was found that improves this meal.",
    replace: "Replace",
    before: "Before",
    after: "After",
    resolvesMandatory: "Resolves mandatory block",
    changedRules: "Affected rules",
    noRecipes: "There are no recipes with nutrition composition for this meal.",
    noPlan: "No active nutrition plan; general Person targets or limits may still apply.",
    planAuthority: "Plan state",
    active_plan: "Active plan",
    partial_plan_coverage: "Partial coverage",
    no_active_plan: "No active plan",
    plan_conflict: "Plan conflict",
    score: "Fit",
    portionNutrition: "Evaluated portion composition",
    portionEnergy: "Portion energy",
    portionUncertain: "Energy unavailable — do not assume zero.",
    nutrientUncertain: "Other nutrients without evidence are not treated as zero.",
    coverageTitle: "Evaluation coverage",
    coverageRules: "Rules evaluated",
    coverageUnknown: "Rules lacking sufficient evidence",
    coverageGuidelines: "Unevaluated guidance",
    coverageBlocks: "Identified mandatory blocks",
    coverageHelp: "Missing data does not demonstrate safety or nutritional suitability. Results depend on the selected portion and recorded sources.",
    provisionalScore: "Some evidence is incomplete or unconfirmed. This score is not a nutrition or FODMAP certification.",
    evidenceSource: "Recorded source",
    missingSource: "Source not supplied",
    eligible: "Eligible",
    blocked: "Blocked",
    mealRules: "Rules for this meal",
    dailyImpact: "Impact on today's targets",
    guidelines: "Unscored guidance",
    safety: "Safety blocks",
    conflicts: "Plan conflicts",
    pass: "Meets",
    partial: "Partial",
    fail: "Fails",
    unknown: "Unknown",
    conflict: "Conflict",
    support: "Supports",
    not_evaluated: "Not evaluated yet",
    mandatory: "Mandatory",
    advisory: "Advisory",
    observed: "Observed",
    projected: "Projected daily total",
    target: "Target",
    breakfast: "Breakfast",
    lunch: "Lunch",
    snack: "Snack",
    dinner: "Dinner",
    loadError: "Could not load recipes.",
    evaluateError: "Could not evaluate this meal.",
    responseMismatch: "The returned assessment does not match the selected person, date, meal or portion. Please evaluate again.",
    transformationError: "Could not calculate improvements for this meal.",
  },
} as const;

function errorText(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return `${error.message} (HTTP ${error.status})`;
  if (error instanceof Error) return error.message;
  return fallback;
}

function initialQuantity(recipe: Recipe): string {
  const composition = recipe.latest_composition;
  if (!composition) return "";
  const reference = Number(composition.reference_quantity);
  const servings = Number(recipe.serving_count);
  if (Number.isFinite(reference) && reference > 0 && Number.isFinite(servings) && servings > 0) {
    const portion = reference / servings;
    return Number.isInteger(portion)
      ? String(portion)
      : portion.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
  }
  return composition.reference_quantity;
}

function targetText(rule: MealPlanFitRule, locale: "pt-PT" | "en"): string {
  const unit = rule.target_unit ? ` ${planFitUnitLabel(rule.target_unit, locale)}` : "";
  if (rule.operator === "range" && rule.target_min !== null && rule.target_max !== null) {
    return `${formatPlanFitNumber(rule.target_min, locale)}–${formatPlanFitNumber(rule.target_max, locale)}${unit}`;
  }
  if (["min", "gte", ">=", ">"].includes(rule.operator) && rule.target_min !== null) {
    return `≥ ${formatPlanFitNumber(rule.target_min, locale)}${unit}`;
  }
  if (["max", "lte", "<=", "<"].includes(rule.operator) && rule.target_max !== null) {
    return `≤ ${formatPlanFitNumber(rule.target_max, locale)}${unit}`;
  }
  if (rule.target_value !== null) return `${formatPlanFitNumber(rule.target_value, locale)}${unit}`;
  return rule.operator;
}

function fitPercent(value: string | null): string {
  if (value === null) return "—";
  return `${Math.round(Number(value) * 100)}%`;
}

export default function MealPlanFitPanel({
  familyId,
  personId,
  planningDate,
  dailyNutritionStateId,
  requestedMealType,
  requireExplicitRecipe = false,
}: {
  familyId: string;
  personId: string;
  planningDate: string;
  dailyNutritionStateId: string | null;
  requestedMealType?: PlanningMealType;
  requireExplicitRecipe?: boolean;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [mealType, setMealType] = useState<PlanningMealType>(requestedMealType ?? "lunch");
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [selectedRecipeId, setSelectedRecipeId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [busy, setBusy] = useState(false);
  const [transformationBusy, setTransformationBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MealPlanFitResult | null>(null);
  const [transformation, setTransformation] = useState<MealTransformationResult | null>(null);
  const evaluationEpoch = useRef(0);
  const transformationEpoch = useRef(0);
  function invalidateEvaluation() {
    evaluationEpoch.current += 1;
    transformationEpoch.current += 1;
    setResult(null);
    setTransformation(null);
    setBusy(false);
    setTransformationBusy(false);
  }
  useEffect(() => {
    // Switching people, dates or daily states invalidates in-flight API responses.
    invalidateEvaluation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [personId, planningDate, dailyNutritionStateId]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void listFamilyRecipes(familyId)
      .then((items) => {
        if (!cancelled) setRecipes(items.filter((recipe) => recipe.is_active));
      })
      .catch((caught: unknown) => {
        if (!cancelled) setError(errorText(caught, copy.loadError));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [familyId, copy.loadError]);

  const availableRecipes = useMemo(
    () =>
      recipes.filter(
        (recipe) =>
          recipe.latest_composition !== null && recipe.suitable_meal_types.includes(mealType),
      ),
    [mealType, recipes],
  );

  useEffect(() => {
    const current = availableRecipes.find((recipe) => recipe.id === selectedRecipeId);
    const next = current ?? (requireExplicitRecipe ? null : availableRecipes[0] ?? null);
    if (!next) {
      setSelectedRecipeId("");
      setQuantity("");
      invalidateEvaluation();
      return;
    }
    if (!current) setSelectedRecipeId(next.id);
    setQuantity(initialQuantity(next));
    invalidateEvaluation();
  }, [availableRecipes, selectedRecipeId, requireExplicitRecipe]);

  const selectedRecipe = availableRecipes.find((recipe) => recipe.id === selectedRecipeId) ?? null;
  const composition = selectedRecipe?.latest_composition ?? null;

  async function runEvaluation() {
    if (!selectedRecipe || !composition) return;
    const numericQuantity = Number(quantity);
    if (!Number.isFinite(numericQuantity) || numericQuantity <= 0) return;

    const epoch = ++evaluationEpoch.current;
    transformationEpoch.current += 1;
    setBusy(true);
    setError(null);
    setTransformation(null);
    try {
      const response = await evaluateMealPlanFit(personId, {
        planning_date: planningDate,
        meal_type: mealType,
        daily_nutrition_state_id: dailyNutritionStateId,
        candidate: {
          candidate_kind: "recipe",
          composition_id: composition.id,
          quantity,
          quantity_unit: composition.reference_unit,
        },
      });
      if (epoch === evaluationEpoch.current) {
        if (planFitMatchesRequest(response,{personId,planningDate,mealType,quantity})) setResult(response);
        else { setResult(null);setError(copy.responseMismatch); }
      }
    } catch (caught: unknown) {
      if (epoch === evaluationEpoch.current) {
        setResult(null);
        setError(errorText(caught, copy.evaluateError));
      }
    } finally {
      if (epoch === evaluationEpoch.current) setBusy(false);
    }
  }

  async function runTransformations() {
    if (!selectedRecipe || !composition || !result) return;
    const epoch = ++transformationEpoch.current;
    setTransformationBusy(true);
    setError(null);
    try {
      const response = await proposeMealTransformations(personId, {
        planning_date: planningDate,
        meal_type: mealType,
        recipe_id: selectedRecipe.id,
        quantity,
        quantity_unit: composition.reference_unit,
        daily_nutrition_state_id: dailyNutritionStateId,
        max_proposals: 5,
      });
      if (epoch === transformationEpoch.current) setTransformation(response);
    } catch (caught: unknown) {
      if (epoch === transformationEpoch.current) {
        setTransformation(null);
        setError(errorText(caught, copy.transformationError));
      }
    } finally {
      if (epoch === transformationEpoch.current) setTransformationBusy(false);
    }
  }

  const scorePercent =
    result?.fit_score === null || result?.fit_score === undefined
      ? null
      : Math.round(Number(result.fit_score) * 100);
  const mealRuleResults = result?.rule_results.filter((rule) => rule.scope !== "daily") ?? [];
  const dailyRuleResults = result?.rule_results.filter((rule) => rule.scope === "daily") ?? [];
  const evidence = result ? planFitEvidenceSummary(result) : null;
  const portionNutrition = result ? planFitCandidateNutrition(result) : null;

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
          <span className={`plan-fit-status status-${rule.status}`}>{copy[rule.status]}</span>
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
        <details className="plan-fit-rule__evidence">
          <summary>{copy.evidenceSource}</summary>
          <p>{planFitEvidenceSource(rule.source, locale).join(" · ") || copy.missingSource}</p>
        </details>
      </article>
    );
  }

  return (
    <section className="plan-fit-panel" aria-labelledby="plan-fit-heading">
      <div className="home-section__heading">
        <div>
          <h3 id="plan-fit-heading">{copy.title}</h3>
          <p>{copy.help}</p>
        </div>
      </div>

      <div className="plan-fit-controls">
        <label className="field">
          <span>{copy.meal}</span>
          <select
            value={mealType}
            onChange={(event) => {
              setMealType(event.target.value as PlanningMealType);
              invalidateEvaluation();
            }}
          >
            {MEAL_TYPES.map((item) => (
              <option key={item} value={item}>
                {copy[item]}
              </option>
            ))}
          </select>
        </label>

        <label className="field plan-fit-controls__recipe">
          <span>{copy.recipe}</span>
          <select
            disabled={loading || availableRecipes.length === 0}
            value={selectedRecipeId}
            onChange={(event) => {
              const nextId = event.target.value;
              setSelectedRecipeId(nextId);
              const nextRecipe = availableRecipes.find((recipe) => recipe.id === nextId);
              if (nextRecipe) setQuantity(initialQuantity(nextRecipe));
              invalidateEvaluation();
            }}
          >
            {requireExplicitRecipe ? <option value="">{copy.chooseActualRecipe}</option> : null}
            {availableRecipes.map((recipe) => (
              <option key={recipe.id} value={recipe.id}>
                {recipe.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field plan-fit-controls__quantity">
          <span>{copy.quantity}</span>
          <div className="plan-fit-quantity">
            <input
              min="0.01"
              step="0.01"
              type="number"
              value={quantity}
              onChange={(event) => {
                setQuantity(event.target.value);
                // Changing the portion must invalidate requests already in flight,
                // not only clear the visible result.
                invalidateEvaluation();
              }}
            />
            <span>{planFitUnitLabel(composition?.reference_unit, locale, quantity)}</span>
          </div>
        </label>

        <button
          className="button primary"
          disabled={busy || !selectedRecipe || !quantity}
          onClick={() => void runEvaluation()}
          type="button"
        >
          {busy ? copy.evaluating : copy.evaluate}
        </button>
      </div>

      {!loading && availableRecipes.length === 0 ? (
        <div className="home-empty">
          <strong>{copy.noRecipes}</strong>
        </div>
      ) : null}
      {error ? (
        <div className="error-banner" role="alert">
          <span>{error}</span>
        </div>
      ) : null}

      {result ? (
        <div className="plan-fit-result">
          <div className="plan-fit-summary">
            <div>
              <span>{copy.score}</span>
              <strong>{scorePercent === null ? "—" : `${scorePercent}%`}</strong>
            </div>
            <div>
              <span>{result.eligible ? copy.eligible : copy.blocked}</span>
              <strong className={`plan-fit-status status-${result.status}`}>{copy[result.status]}</strong>
            </div>
            <div className="plan-fit-summary__plans">
              <span>{copy.planAuthority}</span>
              <strong>
                {copy[result.nutrition_plan_authority.state]}
                {result.active_plans.length > 0
                  ? ` · ${result.active_plans.map((plan) => plan.title).join(" · ")}`
                  : ""}
              </strong>
            </div>
          </div>

          {planFitHasOpenEvidence(result) ? <p className="plan-fit-provisional" role="note">{copy.provisionalScore}</p> : null}

          {portionNutrition ? (
            <section className="plan-fit-portion" aria-label={copy.portionNutrition}>
              <h4>{copy.portionNutrition}</h4>
              <p>{copy.portionEnergy}: {portionNutrition.energyKcal === null
                ? copy.portionUncertain
                : `${formatPlanFitNumber(portionNutrition.energyKcal, locale)} kcal`}</p>
              {portionNutrition.nutrients.length > 0 ? (
                <dl>{portionNutrition.nutrients.map((nutrient)=>(
                  <div key={nutrient.key}>
                    <dt>{planFitTargetLabel(nutrient.key,locale)}</dt>
                    <dd>{formatPlanFitNumber(nutrient.value,locale)} {planFitUnitLabel(nutrient.unit,locale,nutrient.value)}</dd>
                  </div>
                ))}</dl>
              ) : null}
              <small>{copy.nutrientUncertain}</small>
            </section>
          ) : null}

          {evidence ? (
            <section className="plan-fit-coverage" aria-label={copy.coverageTitle}>
              <h4>{copy.coverageTitle}</h4>
              <dl>
                <div><dt>{copy.coverageRules}</dt><dd>{evidence.evaluated}</dd></div>
                <div><dt>{copy.coverageUnknown}</dt><dd>{evidence.unknown}</dd></div>
                <div><dt>{copy.coverageGuidelines}</dt><dd>{evidence.unevaluatedGuidelines}</dd></div>
                <div><dt>{copy.coverageBlocks}</dt><dd>{evidence.blocking}</dd></div>
              </dl>
              <p>{copy.coverageHelp}</p>
            </section>
          ) : null}
          {result.safety_issues.length > 0 ? (
            <div className="plan-fit-alert">
              <strong>{copy.safety}</strong>
              {result.safety_issues.map((issue, index) => (
                <span key={`${issue}:${index}`}>{planFitSafetyIssue(issue, locale)}</span>
              ))}
            </div>
          ) : null}

          {result.conflicts.length > 0 ? (
            <div className="plan-fit-alert">
              <strong>{copy.conflicts}</strong>
              {result.conflicts.map((item) => (
                <span key={item.rule_ids.join(":")}>{planFitConflictMessage(item, locale)}</span>
              ))}
            </div>
          ) : null}

          <div className="meal-transform-actions">
            <div>
              <strong>{copy.improvementsTitle}</strong>
              <span>{copy.improvementsHelp}</span>
            </div>
            <button
              className="button secondary"
              disabled={transformationBusy}
              onClick={() => void runTransformations()}
              type="button"
            >
              {transformationBusy ? copy.improving : copy.improve}
            </button>
          </div>

          {transformation ? (
            <div className="meal-transform-results">
              {transformation.proposals.length === 0 ? (
                <div className="home-empty">
                  <strong>{copy.noImprovements}</strong>
                </div>
              ) : (
                transformation.proposals.map((proposal) => (
                  <article
                    className="meal-transform-proposal"
                    key={`${proposal.operation.recipe_ingredient_id}:${proposal.operation.replacement_food_item_id}`}
                  >
                    <div className="meal-transform-proposal__header">
                      <div>
                        <small>{copy.replace}</small>
                        <strong>
                          {proposal.operation.source_food_name} → {proposal.operation.replacement_food_name}
                        </strong>
                      </div>
                      {proposal.resolves_mandatory_block ? (
                        <span className="plan-fit-status status-pass">{copy.resolvesMandatory}</span>
                      ) : null}
                    </div>
                    <div className="meal-transform-proposal__details">
                      <span>
                        {formatPlanFitNumber(proposal.operation.source_quantity, locale)}{" "}
                        {planFitUnitLabel(
                          proposal.operation.source_unit,
                          locale,
                          proposal.operation.source_quantity,
                        )}
                        {" → "}
                        {formatPlanFitNumber(proposal.operation.replacement_quantity, locale)}{" "}
                        {planFitUnitLabel(
                          proposal.operation.replacement_unit,
                          locale,
                          proposal.operation.replacement_quantity,
                        )}
                      </span>
                      <span>
                        {copy.before}: {fitPercent(proposal.before_fit.fit_score)} · {copy.after}:{" "}
                        {fitPercent(proposal.after_fit.fit_score)}
                      </span>
                      <span>
                        {copy.changedRules}: {proposal.changed_rule_ids.length}
                      </span>
                    </div>
                  </article>
                ))
              )}
            </div>
          ) : null}

          {mealRuleResults.length > 0 ? (
            <div className="plan-fit-rules">
              <h4>{copy.mealRules}</h4>
              {mealRuleResults.map(renderRule)}
            </div>
          ) : null}

          {dailyRuleResults.length > 0 ? (
            <div className="plan-fit-rules">
              <h4>{copy.dailyImpact}</h4>
              {dailyRuleResults.map(renderRule)}
            </div>
          ) : null}

          {result.guideline_results.length > 0 ? (
            <div className="plan-fit-rules">
              <h4>{copy.guidelines}</h4>
              {result.guideline_results.map((guideline) => (
                <article className="plan-fit-rule" key={guideline.guideline_id}>
                  <div className="plan-fit-rule__header">
                    <strong>{guideline.description}</strong>
                    <span className="plan-fit-status status-not_evaluated">{copy.not_evaluated}</span>
                  </div>
                  <p>{planFitGuidelineExplanation(guideline, locale)}</p>
                  <details className="plan-fit-rule__evidence">
                    <summary>{copy.evidenceSource}</summary>
                    <p>{planFitEvidenceSource(guideline.source, locale).join(" · ") || copy.missingSource}</p>
                  </details>
                </article>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
