import { useEffect, useMemo, useState } from "react";

import { ApiError, listFamilyRecipes } from "./api/client";
import { evaluateMealPlanFit } from "./api/planFitClient";
import type { MealPlanFitResult, MealPlanFitRule } from "./api/planFitTypes";
import type { Recipe } from "./api/recipeTypes";
import type { PlanningMealType } from "./api/types";
import { useI18n } from "./i18n";
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

const MEAL_TYPES: PlanningMealType[] = ["breakfast", "lunch", "snack", "dinner"];

const COPY = {
  "pt-PT": {
    title: "Adequação ao plano",
    help: "Testa uma receita e uma porção contra as regras alimentares efetivas desta pessoa.",
    meal: "Refeição",
    recipe: "Receita",
    quantity: "Quantidade",
    evaluate: "Avaliar",
    evaluating: "A avaliar…",
    noRecipes: "Não há receitas com composição nutricional para esta refeição.",
    noPlan: "Nenhum plano alimentar ativo; podem ainda existir metas ou limites gerais da pessoa.",
    activePlan: "Plano ativo",
    activePlans: "Planos ativos",
    score: "Adequação",
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
  },
  en: {
    title: "Plan fit",
    help: "Test a recipe and portion against this person's effective nutrition guidance.",
    meal: "Meal",
    recipe: "Recipe",
    quantity: "Quantity",
    evaluate: "Evaluate",
    evaluating: "Evaluating…",
    noRecipes: "There are no recipes with nutrition composition for this meal.",
    noPlan: "No active nutrition plan; general Person targets or limits may still apply.",
    activePlan: "Active plan",
    activePlans: "Active plans",
    score: "Fit",
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

export default function MealPlanFitPanel({
  familyId,
  personId,
  planningDate,
  dailyNutritionStateId,
}: {
  familyId: string;
  personId: string;
  planningDate: string;
  dailyNutritionStateId: string | null;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [mealType, setMealType] = useState<PlanningMealType>("lunch");
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [selectedRecipeId, setSelectedRecipeId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MealPlanFitResult | null>(null);

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
    const next = current ?? availableRecipes[0] ?? null;
    if (!next) {
      setSelectedRecipeId("");
      setQuantity("");
      setResult(null);
      return;
    }
    if (!current) setSelectedRecipeId(next.id);
    setQuantity(initialQuantity(next));
    setResult(null);
  }, [availableRecipes, selectedRecipeId]);

  const selectedRecipe = availableRecipes.find((recipe) => recipe.id === selectedRecipeId) ?? null;
  const composition = selectedRecipe?.latest_composition ?? null;

  async function runEvaluation() {
    if (!selectedRecipe || !composition) return;
    const numericQuantity = Number(quantity);
    if (!Number.isFinite(numericQuantity) || numericQuantity <= 0) return;

    setBusy(true);
    setError(null);
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
      setResult(response);
    } catch (caught: unknown) {
      setResult(null);
      setError(errorText(caught, copy.evaluateError));
    } finally {
      setBusy(false);
    }
  }

  const scorePercent =
    result?.fit_score === null || result?.fit_score === undefined
      ? null
      : Math.round(Number(result.fit_score) * 100);
  const mealRuleResults = result?.rule_results.filter((rule) => rule.scope !== "daily") ?? [];
  const dailyRuleResults = result?.rule_results.filter((rule) => rule.scope === "daily") ?? [];

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
              setResult(null);
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
              setResult(null);
            }}
          >
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
                setResult(null);
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
              <span>{result.active_plans.length === 1 ? copy.activePlan : copy.activePlans}</span>
              <strong>
                {result.active_plans.length > 0
                  ? result.active_plans.map((plan) => plan.title).join(" · ")
                  : copy.noPlan}
              </strong>
            </div>
          </div>

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
                </article>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
