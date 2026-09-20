import { useEffect, useMemo, useState } from "react";

import {
  ApiError,
  cancelMealPlanEntry,
  getFamilyMealPlan,
  getFamilyRecipe,
} from "./api/client";
import type { FamilyMealPlan, MealPlanEntry, MealType } from "./api/mealPlanTypes";
import { refreshShoppingList } from "./api/pantryShoppingClient";
import type { ShoppingList } from "./api/pantryShoppingTypes";
import { getRecommendationBootstrap } from "./api/recommendationClient";
import { proposeSharedMealTransformations } from "./api/sharedMealTransformationClient";
import type {
  SharedMealTransformationProposal,
  SharedMealTransformationResult,
} from "./api/sharedMealTransformationTypes";
import {
  materializeSharedWeeklyPlan,
  requestSharedWeeklyPlanProposal,
} from "./api/weeklyPlanningClient";
import type {
  SharedWeeklyPlanChoice,
  SharedWeeklyPlanPinnedChoice,
  SharedWeeklyPlanProposal,
  SharedWeeklyPlanSkippedSlot,
  SharedWeeklyPlanProposalRequest,
  SharedWeeklyPlanRequest,
  SharedWeeklyPlanningSlotRequest,
} from "./api/weeklyPlanningTypes";
import type { Recipe } from "./api/recipeTypes";
import type { Person } from "./api/types";
import { useI18n, type Locale } from "./i18n";
import MealPlanFitAssessment from "./MealPlanFitAssessment";
import RecipeEvidencePanel from "./RecipeEvidencePanel";
import { scheduledIso } from "./planning";
import {
  recommendationCandidates,
  recommendationDeliveryProviderKeys,
  recommendationScheduledLocal,
  recommendationSourceKinds,
  type RecommendationSource,
} from "./recommendationPlanning";
import "./weekly-matrix.css";

const ALL_MEAL_TYPES: MealType[] = ["breakfast", "lunch", "snack", "dinner"];
const PREVIEW_MAX_COMBINATIONS = 256;

type BusyStage = "catalogue" | "planning";
type DecisionBusy = "apply" | "reject" | "remove" | null;
type RejectedBySlot = Record<string, string[]>;

export type ShoppingRefreshSummary = {
  automaticNeeded: number;
  planningIssues: number;
};

export function shoppingRefreshSummary(list: ShoppingList): ShoppingRefreshSummary {
  return {
    automaticNeeded: list.items.filter(
      (item) => item.item_source === "automatic" && item.status === "needed",
    ).length,
    planningIssues: list.planning_issues.length,
  };
}

const COPY = {
  "pt-PT": {
    eyebrow: "Semana",
    title: "Plano semanal",
    help: "Vê a semana inteira numa grelha. Escolhe um dia e depois uma refeição para chegar ao detalhe por pessoa.",
    generate: "Gerar proposta",
    regenerate: "Recalcular proposta",
    preparing: "A preparar opções…",
    optimizing: "A optimizar semana…",
    loading: "A carregar semana…",
    preview: "Proposta NutriFlow — revê a semana e aplica-a de uma só vez quando estiver correcta.",
    noPeople: "São necessárias pelo menos duas pessoas para a proposta familiar.",
    noCandidates: "Não existem opções compatíveis para os tempos de refeição ainda em aberto.",
    noOpenSlots: "Esta semana já tem todos os tempos de refeição planeados.",
    noPlan: "Não foi encontrada uma combinação semanal compatível com todas as regras obrigatórias.",
    allOpenSlotsPending: "Não há uma combinação para optimizar porque todos os tempos de refeição ainda em aberto ficaram por decidir. Consulta cada slot para ver o motivo.",
    error: "Não foi possível calcular a proposta semanal",
    exact: "Pesquisa exacta",
    bounded: "Pesquisa optimizada",
    boundedHelp: "Foi avaliado um subconjunto determinístico sem relaxar regras obrigatórias.",
    dayDetail: "Dia",
    chooseMeal: "Escolhe uma refeição para abrir o detalhe.",
    mealDetail: "Refeição",
    planned: "Planeada",
    editPlanned: "Alterar",
    viewPlanned: "Ver",
    removePlanned: "Remover do plano",
    confirmRemovePlanned: "Remover esta refeição do planeamento? O registo fica preservado como cancelado.",
    proposed: "Proposta",
    planAdapted: "Adaptada ao plano",
    preferenceVariant: "Variante por preferência",
    substitution: "Substituição",
    rejectRecipe: "Recusar receita e procurar alternativa",
    empty: "Sem refeição",
    pending: "Por decidir",
    nutritionReason: "Sinais usados na escolha",
    proposedPortion: "Porção proposta",
    mealEnergyReference: "Referência energética da refeição",
    nutritionComposition: "Composição nutricional da porção",
    nutritionPlanComparison: "Comparação com o plano",
    noStructuredPlanTarget: "O plano activo não tem um alvo quantitativo avaliável para estes nutrientes.",
    qualitativePlanGuidance: "Outras indicações relevantes do plano",
    qualitativeNotEvaluated: "Estas indicações são mostradas como contexto e ainda não são avaliadas automaticamente nesta receita.",
    planTarget: "Alvo do plano",
    observed: "Nesta porção",
    adaptToPlan: "Adaptar ao plano",
    suggestAdaptation: "Sugerir adaptação",
    adaptingToPlan: "A procurar adaptações…",
    adaptationActionTitle: "Melhorar esta receita",
    adaptationActionHelp:
      "Procura uma versão da mesma receita que se ajuste melhor aos planos nutricionais e preferências da família, sem piorar a segurança de ninguém.",
    adaptationTitle: "Sugestões de adaptação",
    adaptationHelp: "Substituições avaliadas contra o plano e as preferências da família. Escolhe uma para recalcular a semana antes de a aplicar.",
    useAdaptation: "Usar esta adaptação",
    usingAdaptation: "A recalcular com esta adaptação…",
    adaptationSelected: "A adaptação foi incluída na proposta. Revê a semana antes de a aplicar.",
    adaptationInfeasible:
      "Esta adaptação é segura para a refeição, mas não permite construir uma semana compatível com as restantes regras.",
    useOriginal: "Voltar à receita original",
    originalSelected: "A receita original foi reposta nesta proposta.",
    noAdaptation: "Não foram encontradas substituições seguras configuradas que melhorem esta receita.",
    noSubstitutionProfiles:
      "Esta receita ainda não tem substituições estruturadas configuradas para os seus ingredientes.",
    missingTransformationNutrition:
      "Há um ingrediente substituível sem composição nutricional suficiente.",
    unsupportedTransformationUnit:
      "Há uma quantidade de ingrediente que ainda não pode ser convertida com segurança.",
    missingReplacementNutrition:
      "Uma alternativa possível ainda não tem composição nutricional suficiente.",
    recipeDataLoading: "A carregar qualidade dos dados da receita…",
    recipeDataError: "Não foi possível carregar o detalhe nutricional da receita.",
    planImprovesFor: "Melhora o plano para",
    preferenceImprovesFor: "Melhora as preferências para",
    beforeAfter: "Antes → depois",
    nutritionPlan: "Plano nutricional",
    mealPlanFit: "Avaliação da refeição",
    activePlan: "Activo",
    partialPlanCoverage: "Cobertura parcial",
    noActivePlan: "Sem plano activo",
    planConflict: "Conflito no plano",
    fitPass: "Compatível",
    fitPartial: "Parcial",
    fitFail: "Não compatível",
    fitUnknown: "Não avaliável",
    fitConflict: "Conflito",
    noExplanation: "Sem explicação adicional para esta pessoa.",
    applyWeek: "Aplicar semana",
    applyingWeek: "A validar e aplicar semana…",
    reject: "Recusar e procurar alternativa",
    rejecting: "A procurar alternativa…",
    accepted: "A semana foi guardada no plano.",
    shoppingUpdated: "A lista de compras da semana foi actualizada.",
    shoppingEmpty: "Não há ingredientes automáticos em falta para as refeições calculáveis.",
    shoppingOne: "1 ingrediente automático em falta.",
    shoppingMany: "ingredientes automáticos em falta.",
    shoppingIssueOne: "1 requisito não pôde ser calculado com segurança.",
    shoppingIssueMany: "requisitos não puderam ser calculados com segurança.",
    planRefreshFailed: "A semana foi guardada, mas não foi possível recarregar imediatamente a grelha.",
    shoppingRefreshFailed: "A semana foi guardada, mas não foi possível actualizar a lista de compras.",
    weekdayLunchPending: "Almoço de dia útil: primeiro devem ser usadas sobras reais do jantar anterior; sem sobras, só entra uma opção Uber Eats/Glovo com disponibilidade conhecida. Ainda não existe uma opção automática segura para este slot.",
    unavailableSlot: "Não existem opções disponíveis para este slot com a política actual.",
    leftoversNotice: "As sobras ainda não são inventadas pelo planeador: só serão propostas quando houver quantidade reservada do jantar anterior.",
    breakfast: "Pequeno-almoço",
    lunch: "Almoço",
    snack: "Lanche",
    dinner: "Jantar",
  },
  en: {
    eyebrow: "Week",
    title: "Weekly plan",
    help: "See the whole week in one grid. Choose a day and then a meal to reach Person-specific detail.",
    generate: "Generate proposal",
    regenerate: "Recalculate proposal",
    preparing: "Preparing options…",
    optimizing: "Optimizing week…",
    loading: "Loading week…",
    preview: "NutriFlow proposal — review the week and apply it atomically when it is correct.",
    noPeople: "At least two people are required for a Family proposal.",
    noCandidates: "There are no compatible options for the remaining open meal slots.",
    noOpenSlots: "Every meal slot is already planned for this week.",
    noPlan: "No weekly combination compatible with every mandatory rule was found.",
    allOpenSlotsPending: "There is no combination to optimize because every remaining open meal slot stayed pending. Open each slot to see why.",
    error: "The weekly proposal could not be calculated",
    exact: "Exact search",
    bounded: "Optimized search",
    boundedHelp: "A deterministic subset was evaluated without relaxing mandatory rules.",
    dayDetail: "Day",
    chooseMeal: "Choose a meal to open its detail.",
    mealDetail: "Meal",
    planned: "Planned",
    editPlanned: "Edit",
    viewPlanned: "View",
    removePlanned: "Remove from plan",
    confirmRemovePlanned: "Remove this meal from planning? The record remains preserved as cancelled.",
    proposed: "Proposal",
    planAdapted: "Adapted to plan",
    preferenceVariant: "Preference variant",
    substitution: "Substitution",
    rejectRecipe: "Reject recipe and find alternative",
    empty: "No meal",
    pending: "Pending",
    nutritionReason: "Signals used in selection",
    proposedPortion: "Suggested portion",
    mealEnergyReference: "Meal energy reference",
    nutritionComposition: "Nutrition in the suggested portion",
    nutritionPlanComparison: "Comparison with the plan",
    noStructuredPlanTarget: "The active plan has no evaluable quantitative target for these nutrients.",
    qualitativePlanGuidance: "Other relevant plan guidance",
    qualitativeNotEvaluated: "These instructions are shown as context and are not yet evaluated automatically for this recipe.",
    planTarget: "Plan target",
    observed: "In this portion",
    adaptToPlan: "Adapt to plan",
    suggestAdaptation: "Suggest adaptation",
    adaptingToPlan: "Finding adaptations…",
    adaptationActionTitle: "Improve this recipe",
    adaptationActionHelp:
      "Find a version of the same recipe that better fits the Family nutrition plans and preferences without worsening anyone's safety.",
    adaptationTitle: "Adaptation suggestions",
    adaptationHelp: "Substitutions evaluated against the plan and Family preferences. Choose one to recalculate the week before applying it.",
    useAdaptation: "Use this adaptation",
    usingAdaptation: "Recalculating with this adaptation…",
    adaptationSelected: "The adaptation is now included in the proposal. Review the week before applying it.",
    adaptationInfeasible:
      "This adaptation is safe for the meal, but it does not allow a weekly plan compatible with the remaining rules.",
    useOriginal: "Use original recipe",
    originalSelected: "The original recipe is restored in this proposal.",
    noAdaptation: "No configured safe substitutions were found that improve this recipe.",
    noSubstitutionProfiles:
      "This Recipe does not yet have structured substitutions configured for its ingredients.",
    missingTransformationNutrition:
      "A transformable ingredient does not have enough nutrition composition evidence.",
    unsupportedTransformationUnit:
      "An ingredient quantity cannot yet be converted safely.",
    missingReplacementNutrition:
      "A possible replacement does not yet have enough nutrition composition evidence.",
    recipeDataLoading: "Loading Recipe data quality…",
    recipeDataError: "Could not load the Recipe nutrition detail.",
    planImprovesFor: "Improves the plan for",
    preferenceImprovesFor: "Improves preferences for",
    beforeAfter: "Before → after",
    nutritionPlan: "Nutrition plan",
    mealPlanFit: "Meal evaluation",
    activePlan: "Active",
    partialPlanCoverage: "Partial coverage",
    noActivePlan: "No active plan",
    planConflict: "Plan conflict",
    fitPass: "Compatible",
    fitPartial: "Partial",
    fitFail: "Not compatible",
    fitUnknown: "Not evaluable",
    fitConflict: "Conflict",
    noExplanation: "No additional explanation for this Person.",
    applyWeek: "Apply week",
    applyingWeek: "Validating and applying week…",
    reject: "Reject and find alternative",
    rejecting: "Finding alternative…",
    accepted: "The week was saved to the plan.",
    shoppingUpdated: "The weekly shopping list was refreshed.",
    shoppingEmpty: "There are no automatically generated missing ingredients for calculable meals.",
    shoppingOne: "1 automatically generated ingredient is missing.",
    shoppingMany: "automatically generated ingredients are missing.",
    shoppingIssueOne: "1 requirement could not be calculated safely.",
    shoppingIssueMany: "requirements could not be calculated safely.",
    planRefreshFailed: "The week was saved, but the grid could not be reloaded immediately.",
    shoppingRefreshFailed: "The week was saved, but the shopping list could not be refreshed.",
    weekdayLunchPending: "Weekday lunch: real leftovers from the previous dinner come first; without leftovers, only an Uber Eats/Glovo option with known availability is allowed. There is no safe automatic option for this slot yet.",
    unavailableSlot: "No options are available for this slot under the current policy.",
    leftoversNotice: "The planner does not invent leftovers: they will only be proposed when quantity has been reserved from the previous dinner.",
    breakfast: "Breakfast",
    lunch: "Lunch",
    snack: "Snack",
    dinner: "Dinner",
  },
} as const;

function errorText(error: unknown): string {
  if (error instanceof ApiError) return `${error.message} (HTTP ${error.status})`;
  return error instanceof Error ? error.message : String(error);
}

export function addCalendarDays(isoDate: string, days: number): string {
  const value = new Date(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(value.getTime())) throw new Error("Invalid ISO calendar date.");
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}

export function isWeekendDate(isoDate: string): boolean {
  const weekday = new Date(`${isoDate}T00:00:00Z`).getUTCDay();
  return weekday === 0 || weekday === 6;
}

export function weeklySourcesFor(
  planningDate: string,
  mealType: MealType,
): RecommendationSource[] {
  if (mealType === "breakfast" || mealType === "snack") return ["cooked"];
  if (isWeekendDate(planningDate)) return ["cooked", "restaurant"];
  if (mealType === "lunch") return ["uber_eats", "glovo"];
  return ["cooked"];
}

export function weeklySkippedSlotMessages(
  slots: SharedWeeklyPlanSkippedSlot[],
  locale: Locale,
): Record<string, string> {
  const copy = COPY[locale];
  return Object.fromEntries(
    slots.map((slot) => [
      slot.slot_key,
      slot.meal_type === "lunch" && !isWeekendDate(slot.planning_date)
        ? copy.weekdayLunchPending
        : copy.unavailableSlot,
    ]),
  );
}

export function proposalHasOnlySkippedSlots(
  proposal: SharedWeeklyPlanProposal,
): boolean {
  return (
    proposal.selected_plan === null &&
    proposal.search_space_size === 0 &&
    proposal.evaluated_combinations === 0 &&
    proposal.skipped_slots.length > 0
  );
}


function slotKey(planningDate: string, mealType: MealType): string {
  return `${planningDate}:${mealType}`;
}

function formatDate(value: string, locale: Locale): string {
  return new Intl.DateTimeFormat(locale, {
    weekday: "long",
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function formatGridDay(value: string, locale: Locale): { weekday: string; date: string } {
  const parsed = new Date(`${value}T00:00:00Z`);
  return {
    weekday: new Intl.DateTimeFormat(locale, {
      weekday: "short",
      timeZone: "UTC",
    }).format(parsed),
    date: new Intl.DateTimeFormat(locale, {
      day: "numeric",
      month: "short",
      timeZone: "UTC",
    }).format(parsed),
  };
}

function displayName(person: Person): string {
  return [person.first_name, person.last_name].filter(Boolean).join(" ");
}

function mealLabel(mealType: MealType, locale: Locale): string {
  return COPY[locale][mealType];
}

export function nutritionPlanAuthorityLabel(
  state: SharedWeeklyPlanChoice["participants"][number]["nutrition_plan_authority"],
  locale: Locale,
): string {
  const copy = COPY[locale];
  if (state === "active_plan") return copy.activePlan;
  if (state === "partial_plan_coverage") return copy.partialPlanCoverage;
  if (state === "plan_conflict") return copy.planConflict;
  return copy.noActivePlan;
}

function planFitStatusLabel(
  status: SharedWeeklyPlanChoice["participants"][number]["plan_fit_detail"]["status"],
  locale: Locale,
): string {
  const copy = COPY[locale];
  if (status === "pass") return copy.fitPass;
  if (status === "partial") return copy.fitPartial;
  if (status === "fail") return copy.fitFail;
  if (status === "conflict") return copy.fitConflict;
  return copy.fitUnknown;
}

export function formatMealPortion(
  quantity: string | null,
  unit: string | null,
  energyKcal: string | null,
  locale: Locale,
): string {
  if (quantity === null) return "—";
  const parsedQuantity = Number(quantity);
  const quantityLabel = Number.isFinite(parsedQuantity)
    ? new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(parsedQuantity)
    : quantity;
  const normalizedUnit = (unit ?? "").trim().toLowerCase();
  let unitLabel = unit ?? "";
  if (normalizedUnit === "serving") {
    const singular = Number.isFinite(parsedQuantity) && parsedQuantity <= 1;
    unitLabel =
      locale === "pt-PT"
        ? singular
          ? "porção da receita"
          : "porções da receita"
        : singular
          ? "recipe serving"
          : "recipe servings";
  }
  const energy = energyKcal === null ? null : Number(energyKcal);
  const energyLabel =
    energy !== null && Number.isFinite(energy)
      ? ` · ~${new Intl.NumberFormat(locale, {
          maximumFractionDigits: 0,
          useGrouping: false,
        }).format(energy)} kcal`
      : "";

  return `${quantityLabel}${unitLabel ? ` ${unitLabel}` : ""}${energyLabel}`;
}

export function formatMealEnergyReference(
  minimumKcal: string | null,
  maximumKcal: string | null,
  locale: Locale,
): string | null {
  const minimum = minimumKcal === null ? null : Number(minimumKcal);
  const maximum = maximumKcal === null ? null : Number(maximumKcal);
  const format = (value: number) =>
    new Intl.NumberFormat(locale, {
      maximumFractionDigits: 0,
      useGrouping: false,
    }).format(value);

  if (
    minimum !== null &&
    Number.isFinite(minimum) &&
    maximum !== null &&
    Number.isFinite(maximum)
  ) {
    return `${format(minimum)}–${format(maximum)} kcal`;
  }
  if (minimum !== null && Number.isFinite(minimum)) return `≥ ${format(minimum)} kcal`;
  if (maximum !== null && Number.isFinite(maximum)) return `≤ ${format(maximum)} kcal`;
  return null;
}

type WeeklyNutrition =
  SharedWeeklyPlanChoice["participants"][number]["nutrition"];
type WeeklyPlanRule =
  SharedWeeklyPlanChoice["participants"][number]["plan_fit_detail"]["rule_results"][number];

const NUTRIENT_PRIORITY: Record<string, number> = {
  protein: 0,
  carbohydrate: 1,
  carbohydrates: 1,
  carbs: 1,
  fat: 2,
  total_fat: 2,
  fiber: 3,
  fibre: 3,
  sodium: 4,
  sugar: 5,
  sugars: 5,
};

export function nutrientLabel(key: string, locale: Locale): string {
  const normalized = key.toLowerCase();
  const labels: Record<string, [string, string]> = {
    protein: ["Proteína", "Protein"],
    carbohydrate: ["Hidratos de carbono", "Carbohydrate"],
    carbohydrates: ["Hidratos de carbono", "Carbohydrates"],
    carbs: ["Hidratos de carbono", "Carbs"],
    fat: ["Gordura", "Fat"],
    total_fat: ["Gordura", "Total fat"],
    saturated_fat: ["Gordura saturada", "Saturated fat"],
    fiber: ["Fibra", "Fiber"],
    fibre: ["Fibra", "Fibre"],
    sodium: ["Sódio", "Sodium"],
    sugar: ["Açúcares", "Sugar"],
    sugars: ["Açúcares", "Sugars"],
  };
  const known = labels[normalized];
  if (known) return locale === "pt-PT" ? known[0] : known[1];
  return normalized
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function formatNutritionValue(
  value: string | null,
  unit: string | null,
  locale: Locale,
): string {
  if (value === null) return "—";
  const numeric = Number(value);
  const formatted = Number.isFinite(numeric)
    ? new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(numeric)
    : value;
  return `${formatted}${unit ? ` ${unit}` : ""}`;
}

export function nutritionSummaryRows(
  nutrition: WeeklyNutrition,
  locale: Locale,
): Array<{ key: string; label: string; value: string }> {
  const rows: Array<{ key: string; label: string; value: string }> = [];
  if (nutrition.energy_kcal !== null) {
    rows.push({
      key: "energy",
      label: locale === "pt-PT" ? "Energia" : "Energy",
      value: formatNutritionValue(nutrition.energy_kcal, "kcal", locale),
    });
  }
  const nutrients = Object.entries(nutrition.nutrients)
    .sort(([left], [right]) => {
      const leftRank = NUTRIENT_PRIORITY[left.toLowerCase()] ?? 100;
      const rightRank = NUTRIENT_PRIORITY[right.toLowerCase()] ?? 100;
      return leftRank - rightRank || left.localeCompare(right);
    })
    .slice(0, 6);
  for (const [key, nutrient] of nutrients) {
    rows.push({
      key,
      label: nutrientLabel(key, locale),
      value: formatNutritionValue(nutrient.value, nutrient.unit, locale),
    });
  }
  return rows;
}

export function formatPlanRuleTarget(rule: WeeklyPlanRule, locale: Locale): string {
  const unit = rule.target_unit;
  if (rule.target_min !== null && rule.target_max !== null) {
    return `${formatNutritionValue(rule.target_min, null, locale)}–${formatNutritionValue(
      rule.target_max,
      unit,
      locale,
    )}`;
  }
  if (rule.target_value !== null) {
    return `≈ ${formatNutritionValue(rule.target_value, unit, locale)}`;
  }
  if (rule.target_min !== null) {
    return `≥ ${formatNutritionValue(rule.target_min, unit, locale)}`;
  }
  if (rule.target_max !== null) {
    return `≤ ${formatNutritionValue(rule.target_max, unit, locale)}`;
  }
  return "—";
}

export function planRuleStatusLabel(
  status: WeeklyPlanRule["status"],
  locale: Locale,
): string {
  const pt = locale === "pt-PT";
  if (status === "pass") return pt ? "Dentro do alvo" : "Within target";
  if (status === "fail") return pt ? "Fora do alvo" : "Outside target";
  if (status === "support") return pt ? "Apoia o plano" : "Supports plan";
  return pt ? "Não avaliável" : "Not evaluable";
}

export function numericPlanComparisonRules(
  rules: WeeklyPlanRule[],
): WeeklyPlanRule[] {
  return rules.filter(
    (rule) =>
      rule.target_type === "nutrient" &&
      (rule.observed_value !== null ||
        rule.target_min !== null ||
        rule.target_max !== null ||
        rule.target_value !== null),
  );
}

export function peopleCountLabel(count: number, locale: Locale): string {
  if (locale === "pt-PT") {
    return `${count} ${count === 1 ? "pessoa" : "pessoas"}`;
  }
  return `${count} ${count === 1 ? "person" : "people"}`;
}

export function transformationLimitationLabel(
  limitation: string,
  locale: Locale,
): string | null {
  const copy = COPY[locale];
  if (limitation === "no_structured_substitution_profiles") {
    return copy.noSubstitutionProfiles;
  }
  if (limitation.startsWith("missing_source_composition:")) {
    return copy.missingTransformationNutrition;
  }
  if (limitation.startsWith("unsupported_source_unit:")) {
    return copy.unsupportedTransformationUnit;
  }
  if (
    limitation.startsWith("missing_replacement_composition:") ||
    limitation.startsWith("insufficient_replacement_evidence:")
  ) {
    return copy.missingReplacementNutrition;
  }
  return null;
}

export function adaptationKindLabel(
  proposal: SharedMealTransformationProposal,
  locale: Locale,
): string {
  if (proposal.kind === "plan_adapted") {
    return locale === "pt-PT" ? "Melhora o plano" : "Improves plan";
  }
  return locale === "pt-PT" ? "Variante por preferência" : "Preference variant";
}

export function weeklyExplanationLabel(
  explanation: string,
  locale: Locale,
): string | null {
  const pt = locale === "pt-PT";
  if (
    explanation.startsWith("plan_fit_status:") ||
    explanation === "plan_fit_score_available" ||
    explanation === "plan_fit_score_unavailable"
  ) {
    return null;
  }
  if (explanation === "candidate_fits_meal_energy") {
    return pt
      ? "A porção está ajustada à referência energética desta refeição."
      : "The portion is aligned with this meal's energy reference.";
  }
  if (explanation === "candidate_fits_remaining_energy") {
    return pt
      ? "A porção é compatível com a energia restante do dia."
      : "The portion is compatible with the day's remaining energy.";
  }
  if (explanation === "schedule_preferred_window") {
    return pt
      ? "Está dentro do horário preferido."
      : "It is within the preferred time window.";
  }
  if (explanation === "schedule_available_window") {
    return pt
      ? "Está dentro de um horário disponível."
      : "It is within an available time window.";
  }
  if (explanation.startsWith("planning_location:")) {
    const location = explanation.slice("planning_location:".length);
    return pt ? `Local de preparação: ${location}.` : `Planning location: ${location}.`;
  }
  if (explanation.startsWith("rated:")) {
    const rating = explanation.slice(explanation.lastIndexOf(":") + 1);
    return pt
      ? `Avaliação pessoal desta receita: ${rating}/5.`
      : `Personal recipe rating: ${rating}/5.`;
  }
  if (explanation.startsWith("family_rating:")) {
    const rating = explanation.slice(explanation.lastIndexOf(":") + 1);
    return pt
      ? `Avaliação média da família: ${rating}/5.`
      : `Average family rating: ${rating}/5.`;
  }
  if (explanation.startsWith("preferred:")) {
    return pt ? "Corresponde a uma preferência registada." : "Matches a recorded preference.";
  }
  if (explanation.startsWith("disliked:")) {
    return pt
      ? "Existe uma preferência negativa registada, mas não é impeditiva."
      : "A negative preference is recorded, but it is not blocking.";
  }
  if (explanation.startsWith("advisory_reaction:")) {
    return pt
      ? "Existe uma reacção alimentar não obrigatória registada."
      : "A non-mandatory food reaction is recorded.";
  }
  if (explanation.startsWith("exceeds_remaining_max:")) {
    const nutrient = explanation.slice("exceeds_remaining_max:".length).replaceAll("_", " ");
    return pt
      ? `Ultrapassa o máximo restante de ${nutrient}.`
      : `Exceeds the remaining maximum for ${nutrient}.`;
  }
  return null;
}

export function weeklyExplanationLabels(
  explanations: string[],
  locale: Locale,
): string[] {
  return explanations
    .map((explanation) => weeklyExplanationLabel(explanation, locale))
    .filter((explanation): explanation is string => explanation !== null);
}

function entryName(entry: MealPlanEntry): string {
  return entry.recipe_name ?? entry.title ?? "—";
}

export function mealEntryFor(
  plan: FamilyMealPlan,
  planningDate: string,
  mealType: MealType,
): MealPlanEntry | null {
  const day = plan.days.find((candidate) => candidate.date === planningDate);
  const slot = day?.slots.find((candidate) => candidate.meal_type === mealType);
  return slot?.meals[0] ?? null;
}

export function choicesByDate(
  choices: SharedWeeklyPlanChoice[],
): Map<string, SharedWeeklyPlanChoice[]> {
  const grouped = new Map<string, SharedWeeklyPlanChoice[]>();
  for (const choice of choices) {
    const current = grouped.get(choice.planning_date) ?? [];
    current.push(choice);
    current.sort(
      (left, right) =>
        ALL_MEAL_TYPES.indexOf(left.meal_type) - ALL_MEAL_TYPES.indexOf(right.meal_type),
    );
    grouped.set(choice.planning_date, current);
  }
  return grouped;
}

export function upsertPinnedWeeklyChoice(
  choices: SharedWeeklyPlanPinnedChoice[],
  next: SharedWeeklyPlanPinnedChoice,
): SharedWeeklyPlanPinnedChoice[] {
  return [
    ...choices.filter((choice) => choice.slot_key !== next.slot_key),
    next,
  ];
}

export function pinnedChoiceForAdaptation(
  choice: SharedWeeklyPlanChoice,
  adaptation: SharedMealTransformationProposal,
): SharedWeeklyPlanPinnedChoice {
  return {
    slot_key: choice.slot_key,
    candidate_key: choice.candidate_key,
    recipe_ingredient_id: adaptation.operation.recipe_ingredient_id,
    replacement_food_item_id: adaptation.operation.replacement_food_item_id,
  };
}

export function pinnedChoiceForOriginal(
  choice: SharedWeeklyPlanChoice,
): SharedWeeklyPlanPinnedChoice {
  return {
    slot_key: choice.slot_key,
    candidate_key: choice.candidate_key,
  };
}

export function weeklyPlanRequest(
  proposal: SharedWeeklyPlanProposalRequest,
  choices: SharedWeeklyPlanChoice[],
): SharedWeeklyPlanRequest {
  return {
    ...proposal,
    expected_choices: choices.map((choice) => ({
      slot_key: choice.slot_key,
      candidate_key: choice.candidate_key,
      ...(choice.transformation
        ? {
            recipe_ingredient_id:
              choice.transformation.operation.recipe_ingredient_id,
            replacement_food_item_id:
              choice.transformation.operation.replacement_food_item_id,
          }
        : {}),
    })),
  };
}


function choiceFor(
  choices: Map<string, SharedWeeklyPlanChoice[]>,
  planningDate: string,
  mealType: MealType,
): SharedWeeklyPlanChoice | null {
  return choices.get(planningDate)?.find((choice) => choice.meal_type === mealType) ?? null;
}

function sourceKindsFor(sources: RecommendationSource[]): string[] {
  const kinds = [...recommendationSourceKinds(sources)];
  if (sources.includes("cooked") && !kinds.includes("pantry")) kinds.push("pantry");
  return kinds;
}

export default function WeeklyProposalPreview({
  familyId,
  weekStart,
  people,
  plan: suppliedPlan,
  onEdit,
  onPlanChanged,
}: {
  familyId: string;
  weekStart?: string;
  people: Person[];
  plan?: FamilyMealPlan;
  onEdit?: (planningDate: string, mealType: MealType, entry: MealPlanEntry | null) => void;
  onPlanChanged?: () => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [loadedPlan, setLoadedPlan] = useState<FamilyMealPlan | null>(null);
  const [refreshedPlan, setRefreshedPlan] = useState<FamilyMealPlan | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [proposal, setProposal] = useState<SharedWeeklyPlanProposal | null>(null);
  const [proposalRequest, setProposalRequest] = useState<SharedWeeklyPlanProposalRequest | null>(null);
  const [skippedSlots, setSkippedSlots] = useState<Record<string, string>>({});
  const [rejectedBySlot, setRejectedBySlot] = useState<RejectedBySlot>({});
  const [busy, setBusy] = useState(false);
  const [busyStage, setBusyStage] = useState<BusyStage | null>(null);
  const [decisionBusy, setDecisionBusy] = useState<DecisionBusy>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [shoppingSummary, setShoppingSummary] = useState<ShoppingRefreshSummary | null>(null);
  const [planRefreshWarning, setPlanRefreshWarning] = useState<string | null>(null);
  const [shoppingWarning, setShoppingWarning] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [selectedMealType, setSelectedMealType] = useState<MealType | null>(null);
  const [adaptationBusy, setAdaptationBusy] = useState(false);
  const [adaptationResult, setAdaptationResult] =
    useState<SharedMealTransformationResult | null>(null);
  const [adaptationError, setAdaptationError] = useState<string | null>(null);
  const [pinnedChoices, setPinnedChoices] = useState<SharedWeeklyPlanPinnedChoice[]>([]);
  const [adaptationChoiceBusy, setAdaptationChoiceBusy] = useState<string | null>(null);
  const [selectedRecipeDetail, setSelectedRecipeDetail] = useState<Recipe | null>(null);
  const [recipeDetailLoading, setRecipeDetailLoading] = useState(false);
  const [recipeDetailError, setRecipeDetailError] = useState<string | null>(null);
  const plan = refreshedPlan ?? suppliedPlan ?? loadedPlan;
  const effectiveWeekStart = refreshedPlan?.start_date ?? suppliedPlan?.start_date ?? weekStart;

  useEffect(() => {
    setRefreshedPlan(null);
    setProposal(null);
    setProposalRequest(null);
    setRejectedBySlot({});
    setSkippedSlots({});
    setNotice(null);
    setShoppingSummary(null);
    setPlanRefreshWarning(null);
    setShoppingWarning(null);
    setAdaptationResult(null);
    setAdaptationError(null);
    setAdaptationBusy(false);
    setPinnedChoices([]);
    setAdaptationChoiceBusy(null);
    setSelectedRecipeDetail(null);
    setRecipeDetailLoading(false);
    setRecipeDetailError(null);
  }, [familyId, weekStart]);

  useEffect(() => {
    if (suppliedPlan || !weekStart) return;
    let cancelled = false;
    setLoadError(null);
    void getFamilyMealPlan(familyId, weekStart, 7)
      .then((result) => {
        if (!cancelled) setLoadedPlan(result);
      })
      .catch((caught: unknown) => {
        if (!cancelled) setLoadError(errorText(caught));
      });
    return () => {
      cancelled = true;
    };
  }, [familyId, suppliedPlan, weekStart]);

  const peopleById = useMemo(
    () => new Map(people.map((person) => [person.id, person])),
    [people],
  );
  const grouped = useMemo(
    () => choicesByDate(proposal?.selected_plan?.choices ?? []),
    [proposal],
  );
  const weekDates = useMemo(
    () =>
      effectiveWeekStart
        ? Array.from({ length: 7 }, (_, dayOffset) =>
            addCalendarDays(effectiveWeekStart, dayOffset),
          )
        : [],
    [effectiveWeekStart],
  );
  const selectedEntry =
    plan && selectedDate && selectedMealType
      ? mealEntryFor(plan, selectedDate, selectedMealType)
      : null;
  const selectedChoice =
    selectedDate && selectedMealType
      ? choiceFor(grouped, selectedDate, selectedMealType)
      : null;
  const selectedChoiceHasPlan =
    selectedChoice?.participants.some(
      (participant) => participant.nutrition_plan_authority !== "no_active_plan",
    ) ?? false;
  const selectedSlotKey =
    selectedDate && selectedMealType ? slotKey(selectedDate, selectedMealType) : null;
  const selectedSkippedReason = selectedSlotKey ? skippedSlots[selectedSlotKey] ?? null : null;

  useEffect(() => {
    const recipeId = selectedChoice?.recipe_id;
    if (!recipeId) {
      setSelectedRecipeDetail(null);
      setRecipeDetailLoading(false);
      setRecipeDetailError(null);
      return;
    }
    let cancelled = false;
    setSelectedRecipeDetail(null);
    setRecipeDetailLoading(true);
    setRecipeDetailError(null);
    void getFamilyRecipe(familyId, recipeId)
      .then((recipe) => {
        if (!cancelled) setSelectedRecipeDetail(recipe);
      })
      .catch(() => {
        if (!cancelled) setRecipeDetailError(copy.recipeDataError);
      })
      .finally(() => {
        if (!cancelled) setRecipeDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [familyId, selectedChoice?.recipe_id, copy.recipeDataError]);

  useEffect(() => {
    setAdaptationResult(null);
    setAdaptationError(null);
    setAdaptationBusy(false);
  }, [selectedChoice?.slot_key, selectedChoice?.candidate_key, selectedChoice?.recipe_id]);

  async function suggestAdaptations() {
    if (!selectedChoice?.recipe_id) return;
    setAdaptationBusy(true);
    setAdaptationError(null);
    setAdaptationResult(null);
    try {
      const result = await proposeSharedMealTransformations(familyId, {
        planning_date: selectedChoice.planning_date,
        meal_type: selectedChoice.meal_type,
        recipe_id: selectedChoice.recipe_id,
        participants: selectedChoice.participants.map((participant) => ({
          person_id: participant.person_id,
          daily_nutrition_state_id: participant.daily_nutrition_state_id,
          quantity: participant.quantity,
          quantity_unit: participant.quantity_unit,
        })),
        max_proposals: 5,
      });
      setAdaptationResult(result);
    } catch (caught: unknown) {
      setAdaptationError(errorText(caught));
    } finally {
      setAdaptationBusy(false);
    }
  }

  async function generateProposal(
    rejectedOverride: RejectedBySlot = rejectedBySlot,
    resetSelection = true,
    pinnedOverride: SharedWeeklyPlanPinnedChoice[] = pinnedChoices,
  ) {
    setBusy(true);
    setBusyStage("catalogue");
    setError(null);
    setNotice(null);
    setShoppingSummary(null);
    setPlanRefreshWarning(null);
    setShoppingWarning(null);
    setProposal(null);
    if (resetSelection) setSelectedMealType(null);
    try {
      if (!plan) throw new Error(copy.loading);
      if (people.length < 2) throw new Error(copy.noPeople);
      const firstPerson = people[0];
      if (!firstPerson) throw new Error(copy.noPeople);

      const targets = weekDates.flatMap((planningDate) =>
        ALL_MEAL_TYPES.flatMap((mealType) =>
          mealEntryFor(plan, planningDate, mealType) === null
            ? [{ planningDate, mealType }]
            : [],
        ),
      );
      if (targets.length === 0) throw new Error(copy.noOpenSlots);

      const planningDates = [...new Set(targets.map((target) => target.planningDate))];
      const catalogueEntries = await Promise.all(
        planningDates.map(async (planningDate) => {
          const bootstrapScheduledAt = scheduledIso(
            recommendationScheduledLocal(planningDate, "lunch"),
          );
          const bootstrap = await getRecommendationBootstrap(
            firstPerson.id,
            bootstrapScheduledAt,
            { ensureState: false },
          );
          return [planningDate, bootstrap.candidates] as const;
        }),
      );
      const catalogues = new Map(catalogueEntries);
      const skipped: Record<string, string> = {};
      const slots: SharedWeeklyPlanningSlotRequest[] = [];

      for (const { planningDate, mealType } of targets) {
        const key = slotKey(planningDate, mealType);
        const sources = weeklySourcesFor(planningDate, mealType);
        const rejected = new Set(rejectedOverride[key] ?? []);
        const catalogue = (catalogues.get(planningDate) ?? []).filter(
          (candidate) => !rejected.has(candidate.catalog_key),
        );
        const candidates = recommendationCandidates(catalogue, sources, mealType);
        if (candidates.length === 0) {
          skipped[key] =
            mealType === "lunch" && !isWeekendDate(planningDate)
              ? copy.weekdayLunchPending
              : copy.unavailableSlot;
          continue;
        }

        const sourceKinds = sourceKindsFor(sources);
        const commercial = sources.some((source) => source !== "cooked");
        slots.push({
          slot_key: key,
          planning_date: planningDate,
          scheduled_at: scheduledIso(recommendationScheduledLocal(planningDate, mealType)),
          meal_type: mealType,
          candidates,
          location: commercial ? null : "Casa",
          available_minutes: null,
          has_kitchen: sources.includes("cooked"),
          source_kinds: sourceKinds,
          delivery_provider_keys: recommendationDeliveryProviderKeys(sources),
          provisional_history: [],
          auto_size_portions: true,
        });
      }
      setSkippedSlots(skipped);
      if (slots.length === 0) throw new Error(copy.noCandidates);

      const request: SharedWeeklyPlanProposalRequest = {
        person_ids: people.map((person) => person.id),
        slots,
        pinned_choices: pinnedOverride,
        max_combinations: PREVIEW_MAX_COMBINATIONS,
      };
      setProposalRequest(request);
      setBusyStage("planning");
      const result = await requestSharedWeeklyPlanProposal(familyId, request);
      const serverSkipped = weeklySkippedSlotMessages(
        result.skipped_slots,
        locale,
      );
      setSkippedSlots({ ...skipped, ...serverSkipped });
      setProposal(result);
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
      setBusyStage(null);
    }
  }

  async function recalculateWithPinnedChoices(
    nextPinnedChoices: SharedWeeklyPlanPinnedChoice[],
    successMessage: string,
  ) {
    if (!proposalRequest || !selectedChoice) return;
    const selectedKey = selectedChoice.slot_key;
    setAdaptationChoiceBusy(selectedKey);
    setAdaptationError(null);
    setError(null);
    setNotice(null);
    try {
      const request: SharedWeeklyPlanProposalRequest = {
        ...proposalRequest,
        pinned_choices: nextPinnedChoices,
      };
      const result = await requestSharedWeeklyPlanProposal(familyId, request);
      if (result.selected_plan === null) {
        setAdaptationError(copy.adaptationInfeasible);
        return;
      }
      const serverSkipped = weeklySkippedSlotMessages(result.skipped_slots, locale);
      const requestedSlotKeys = new Set(request.slots.map((slot) => slot.slot_key));
      const localSkipped = Object.fromEntries(
        Object.entries(skippedSlots).filter(([key]) => !requestedSlotKeys.has(key)),
      );
      setSkippedSlots({ ...localSkipped, ...serverSkipped });
      setPinnedChoices(nextPinnedChoices);
      setProposalRequest(request);
      setProposal(result);
      setAdaptationResult(null);
      setNotice(successMessage);
    } catch (caught: unknown) {
      setAdaptationError(errorText(caught));
    } finally {
      setAdaptationChoiceBusy(null);
    }
  }

  async function useAdaptation(adaptation: SharedMealTransformationProposal) {
    if (!selectedChoice) return;
    const nextPinnedChoices = upsertPinnedWeeklyChoice(
      pinnedChoices,
      pinnedChoiceForAdaptation(selectedChoice, adaptation),
    );
    await recalculateWithPinnedChoices(nextPinnedChoices, copy.adaptationSelected);
  }

  async function useOriginalRecipe() {
    if (!selectedChoice) return;
    const nextPinnedChoices = upsertPinnedWeeklyChoice(
      pinnedChoices,
      pinnedChoiceForOriginal(selectedChoice),
    );
    await recalculateWithPinnedChoices(nextPinnedChoices, copy.originalSelected);
  }

  async function applyWeek() {
    if (!proposalRequest || !proposal?.selected_plan || !effectiveWeekStart) return;
    setDecisionBusy("apply");
    setError(null);
    setNotice(null);
    setShoppingSummary(null);
    setPlanRefreshWarning(null);
    setShoppingWarning(null);

    try {
      await materializeSharedWeeklyPlan(
        familyId,
        weeklyPlanRequest(proposalRequest, proposal.selected_plan.choices),
      );
    } catch (caught: unknown) {
      setError(errorText(caught));
      setDecisionBusy(null);
      return;
    }

    setProposal(null);
    setProposalRequest(null);
    setRejectedBySlot({});
    setPinnedChoices([]);
    setSkippedSlots({});
    setNotice(copy.accepted);

    try {
      const updated = await getFamilyMealPlan(familyId, effectiveWeekStart, 7);
      setRefreshedPlan(updated);
    } catch (reloadError: unknown) {
      setPlanRefreshWarning(errorText(reloadError));
    }

    try {
      const shoppingList = await refreshShoppingList(familyId, effectiveWeekStart, 7);
      setShoppingSummary(shoppingRefreshSummary(shoppingList));
    } catch (shoppingError: unknown) {
      setShoppingWarning(errorText(shoppingError));
    } finally {
      setDecisionBusy(null);
    }
  }

  async function removeSelectedEntry() {
    if (
      !selectedEntry ||
      selectedEntry.status !== "planned" ||
      !effectiveWeekStart ||
      !window.confirm(copy.confirmRemovePlanned)
    ) {
      return;
    }
    setDecisionBusy("remove");
    setError(null);
    setNotice(null);
    try {
      await cancelMealPlanEntry(familyId, selectedEntry.id);
      const updated = await getFamilyMealPlan(familyId, effectiveWeekStart, 7);
      setRefreshedPlan(updated);
      setProposal(null);
      setProposalRequest(null);
      setRejectedBySlot({});
      setPinnedChoices([]);
      setSkippedSlots({});
      setSelectedMealType(null);
      onPlanChanged?.();
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setDecisionBusy(null);
    }
  }


  async function rejectSelectedChoice() {
    if (!selectedChoice) return;
    const key = selectedChoice.slot_key;
    const existing = rejectedBySlot[key] ?? [];
    const next: RejectedBySlot = {
      ...rejectedBySlot,
      [key]: [...new Set([...existing, selectedChoice.candidate_key])],
    };
    const nextPinnedChoices = pinnedChoices.filter(
      (choice) => choice.slot_key !== key,
    );
    setRejectedBySlot(next);
    setPinnedChoices(nextPinnedChoices);
    setDecisionBusy("reject");
    setError(null);
    setNotice(null);
    try {
      await generateProposal(next, false, nextPinnedChoices);
    } finally {
      setDecisionBusy(null);
    }
  }

  function selectDay(planningDate: string) {
    setSelectedDate(planningDate);
    setSelectedMealType(null);
  }

  function selectMeal(planningDate: string, mealType: MealType) {
    setSelectedDate(planningDate);
    setSelectedMealType(mealType);
  }

  return (
    <section className="meal-plan-editor weekly-proposal-preview">
      <div className="meal-plan-editor__heading">
        <div>
          <span className="eyebrow">{copy.eyebrow}</span>
          <h2>{copy.title}</h2>
          <p>{copy.help}</p>
        </div>
        <div className="meal-plan-editor__actions">
          {proposal?.selected_plan ? (
            <button
              className="button primary"
              disabled={
                busy ||
                decisionBusy !== null ||
                proposalRequest === null ||
                adaptationChoiceBusy !== null
              }
              onClick={() => void applyWeek()}
              type="button"
            >
              {decisionBusy === "apply" ? copy.applyingWeek : copy.applyWeek}
            </button>
          ) : null}
          <button
            className={proposal?.selected_plan ? "button ghost" : "button primary"}
            disabled={
              busy ||
              decisionBusy !== null ||
              adaptationChoiceBusy !== null ||
              people.length < 2 ||
              !plan
            }
            onClick={() => void generateProposal()}
            type="button"
          >
            {busy
              ? busyStage === "catalogue"
                ? copy.preparing
                : copy.optimizing
              : proposal
                ? copy.regenerate
                : copy.generate}
          </button>
        </div>
      </div>

      {people.length < 2 ? <div className="family-meals-empty-day">{copy.noPeople}</div> : null}
      {loadError ? (
        <div className="error-banner" role="alert">
          <strong>{copy.error}</strong><span>{loadError}</span>
        </div>
      ) : null}
      {error ? (
        <div className="error-banner" role="alert">
          <strong>{copy.error}</strong><span>{error}</span>
        </div>
      ) : null}
      {notice ? <div className="decision-result" role="status"><strong>{notice}</strong></div> : null}
      {shoppingSummary ? (
        <div className="decision-result" role="status">
          <strong>{copy.shoppingUpdated}</strong>
          <span>
            {shoppingSummary.automaticNeeded === 0
              ? copy.shoppingEmpty
              : shoppingSummary.automaticNeeded === 1
                ? copy.shoppingOne
                : `${shoppingSummary.automaticNeeded} ${copy.shoppingMany}`}
            {shoppingSummary.planningIssues > 0
              ? ` · ${
                  shoppingSummary.planningIssues === 1
                    ? copy.shoppingIssueOne
                    : `${shoppingSummary.planningIssues} ${copy.shoppingIssueMany}`
                }`
              : ""}
          </span>
        </div>
      ) : null}
      {planRefreshWarning ? (
        <div className="error-banner" role="alert">
          <strong>{copy.planRefreshFailed}</strong>
          <span>{planRefreshWarning}</span>
        </div>
      ) : null}
      {shoppingWarning ? (
        <div className="error-banner" role="alert">
          <strong>{copy.shoppingRefreshFailed}</strong>
          <span>{shoppingWarning}</span>
        </div>
      ) : null}
      {proposal ? (
        <div className="decision-result" role="status">
          <strong>{copy.preview}</strong>
          <span>
            {proposal.search_strategy === "exact" ? copy.exact : copy.bounded}
            {proposal.search_truncated ? ` · ${copy.boundedHelp}` : ""}
          </span>
        </div>
      ) : null}
      {proposal && !proposal.selected_plan ? (
        <div className="family-meals-empty-day">
          {proposalHasOnlySkippedSlots(proposal) ? copy.allOpenSlotsPending : copy.noPlan}
        </div>
      ) : null}

      {!plan ? (
        <div className="shell-loading" role="status">{copy.loading}</div>
      ) : (
        <>
          <div className="weekly-calendar-scroll">
            <div className="weekly-day-grid" role="grid" aria-label={copy.title}>
              {weekDates.map((planningDate) => {
                const gridDay = formatGridDay(planningDate, locale);
                return (
                  <article
                    className={`weekly-grid-day ${selectedDate === planningDate ? "selected" : ""}`}
                    key={planningDate}
                  >
                    <button
                      className="weekly-grid-day__date-button"
                      onClick={() => selectDay(planningDate)}
                      type="button"
                    >
                      <strong>{gridDay.weekday}</strong>
                      <small>{gridDay.date}</small>
                    </button>
                    <div className="weekly-grid-day__meals">
                      {ALL_MEAL_TYPES.map((mealType) => {
                        const entry = mealEntryFor(plan, planningDate, mealType);
                        const choice = choiceFor(grouped, planningDate, mealType);
                        const pendingReason = skippedSlots[slotKey(planningDate, mealType)];
                        const state = entry ? "planned" : choice ? "proposed" : "empty";
                        const label = entry
                          ? entryName(entry)
                          : choice?.candidate_name ?? (pendingReason ? copy.pending : copy.empty);
                        return (
                          <button
                            aria-pressed={
                              selectedDate === planningDate && selectedMealType === mealType
                            }
                            className={`weekly-grid-meal is-${state} ${
                              selectedDate === planningDate && selectedMealType === mealType
                                ? "selected"
                                : ""
                            }`}
                            key={mealType}
                            onClick={() => selectMeal(planningDate, mealType)}
                            type="button"
                          >
                            <span className="weekly-grid-meal__label">
                              <small>{mealLabel(mealType, locale)}</small>
                              <em>
                                {entry
                                  ? copy.planned
                                  : choice
                                    ? copy.proposed
                                    : pendingReason
                                      ? copy.pending
                                      : copy.empty}
                              </em>
                            </span>
                            <strong>{label}</strong>
                            {entry?.transformations[0] ? (
                              <small className="weekly-grid-transformation">
                                {entry.transformations[0].transformation_kind === "plan_adapted"
                                  ? copy.planAdapted
                                  : copy.preferenceVariant}
                              </small>
                            ) : choice?.transformation ? (
                              <small className="weekly-grid-transformation">
                                {choice.transformation.kind === "plan_adapted"
                                  ? copy.planAdapted
                                  : copy.preferenceVariant}
                              </small>
                            ) : null}
                          </button>
                        );
                      })}
                    </div>
                  </article>
                );
              })}
            </div>
          </div>

          {selectedDate ? (
            <section className="weekly-day-detail">
              <div className="weekly-section-heading">
                <div>
                  <span className="eyebrow">{copy.dayDetail}</span>
                  <h3>{formatDate(selectedDate, locale)}</h3>
                  <p>{copy.chooseMeal}</p>
                </div>
              </div>
              <div className="weekly-day-meals">
                {ALL_MEAL_TYPES.map((mealType) => {
                  const entry = mealEntryFor(plan, selectedDate, mealType);
                  const choice = choiceFor(grouped, selectedDate, mealType);
                  const pendingReason = skippedSlots[slotKey(selectedDate, mealType)];
                  return (
                    <button
                      aria-pressed={selectedMealType === mealType}
                      className={`weekly-day-meal ${selectedMealType === mealType ? "selected" : ""}`}
                      key={mealType}
                      onClick={() => setSelectedMealType(mealType)}
                      type="button"
                    >
                      <span>
                        <small>{mealLabel(mealType, locale)}</small>
                        <strong>
                          {entry
                            ? entryName(entry)
                            : choice?.candidate_name ?? (pendingReason ? copy.pending : copy.empty)}
                        </strong>
                      </span>
                      <span className="weekly-day-meal__meta">
                        {entry
                          ? copy.planned
                          : choice
                            ? copy.proposed
                            : pendingReason
                              ? copy.pending
                              : copy.empty}
                        <span aria-hidden="true"> ›</span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </section>
          ) : null}

          {selectedDate && selectedMealType ? (
            <section className="weekly-meal-detail">
              <div className="weekly-section-heading weekly-meal-detail__heading">
                <div>
                  <span className="eyebrow">{copy.mealDetail}</span>
                  <h3>
                    {selectedEntry
                      ? entryName(selectedEntry)
                      : selectedChoice?.candidate_name ?? mealLabel(selectedMealType, locale)}
                  </h3>
                  <p>
                    {formatDate(selectedDate, locale)} · {mealLabel(selectedMealType, locale)}
                  </p>
                </div>
                {selectedEntry ? (
                  <div className="weekly-meal-detail__actions">
                    {onEdit ? (
                      <button
                        className="button ghost"
                        disabled={selectedEntry.status !== "planned" || decisionBusy !== null}
                        onClick={() => onEdit(selectedDate, selectedMealType, selectedEntry)}
                        type="button"
                      >
                        {selectedEntry.transformations.length > 0
                          ? copy.viewPlanned
                          : copy.editPlanned}
                      </button>
                    ) : null}
                    <button
                      className="button ghost"
                      disabled={selectedEntry.status !== "planned" || decisionBusy !== null}
                      onClick={() => void removeSelectedEntry()}
                      type="button"
                    >
                      {copy.removePlanned}
                    </button>
                  </div>
                ) : null}
              </div>

              {selectedEntry ? (
                <>
                  {selectedEntry.transformations.map((transformation) => (
                    <div className="weekly-transformation-summary" key={transformation.id}>
                      <span className="weekly-transformation-summary__kind">
                        {transformation.transformation_kind === "plan_adapted"
                          ? copy.planAdapted
                          : copy.preferenceVariant}
                      </span>
                      <div>
                        <small>{copy.substitution}</small>
                        <strong>
                          {transformation.source_food_name} →{" "}
                          {transformation.replacement_food_name}
                        </strong>
                      </div>
                    </div>
                  ))}
                  <div className="weekly-person-detail-list">
                    {selectedEntry.participants.map((participant) => (
                      <article className="weekly-person-detail" key={participant.person_id}>
                        <div className="weekly-person-detail__heading">
                          <strong>
                            {[participant.first_name, participant.last_name]
                              .filter(Boolean)
                              .join(" ")}
                          </strong>
                          <span>
                            {formatMealPortion(
                              participant.quantity,
                              participant.unit,
                              participant.energy_kcal,
                              locale,
                            )}
                          </span>
                        </div>
                      </article>
                    ))}
                  </div>
                </>
              ) : selectedChoice ? (
                <>
                  {selectedChoice.recipe_id ? (
                    <div className="meal-transform-actions weekly-meal-adaptation-action">
                      <div>
                        <strong>{copy.adaptationActionTitle}</strong>
                        <span>{copy.adaptationActionHelp}</span>
                      </div>
                      <button
                        className="button secondary"
                        disabled={
                          busy ||
                          decisionBusy !== null ||
                          adaptationBusy ||
                          adaptationChoiceBusy !== null
                        }
                        onClick={() => void suggestAdaptations()}
                        type="button"
                      >
                        {adaptationBusy
                          ? copy.adaptingToPlan
                          : selectedChoiceHasPlan
                            ? copy.adaptToPlan
                            : copy.suggestAdaptation}
                      </button>
                    </div>
                  ) : null}
                  {selectedChoice.recipe_id ? (
                    selectedRecipeDetail ? (
                      <RecipeEvidencePanel recipe={selectedRecipeDetail} />
                    ) : recipeDetailLoading ? (
                      <p className="muted compact">{copy.recipeDataLoading}</p>
                    ) : recipeDetailError ? (
                      <p className="muted compact">{recipeDetailError}</p>
                    ) : null
                  ) : null}
                  {selectedChoice.transformation ? (
                    <div className="weekly-transformation-summary">
                      <span className="weekly-transformation-summary__kind">
                        {selectedChoice.transformation.kind === "plan_adapted"
                          ? copy.planAdapted
                          : copy.preferenceVariant}
                      </span>
                      <div>
                        <small>{copy.substitution}</small>
                        <strong>
                          {selectedChoice.transformation.operation.source_food_name} →{" "}
                          {selectedChoice.transformation.operation.replacement_food_name}
                        </strong>
                      </div>
                      <button
                        className="button ghost"
                        disabled={
                          busy ||
                          decisionBusy !== null ||
                          adaptationBusy ||
                          adaptationChoiceBusy !== null
                        }
                        onClick={() => void useOriginalRecipe()}
                        type="button"
                      >
                        {copy.useOriginal}
                      </button>
                    </div>
                  ) : null}
                  <div className="weekly-person-detail-list">
                    {selectedChoice.participants.map((participant) => {
                      const person = peopleById.get(participant.person_id);
                      const energyReference = formatMealEnergyReference(
                        participant.meal_energy_target_min_kcal,
                        participant.meal_energy_target_max_kcal,
                        locale,
                      );
                      const explanationLabels = weeklyExplanationLabels(
                        participant.explanation,
                        locale,
                      );
                      return (
                        <article className="weekly-person-detail" key={participant.person_id}>
                          <div className="weekly-person-detail__heading">
                            <strong>{person ? displayName(person) : participant.person_id}</strong>
                            <span>
                              {copy.proposedPortion}:{" "}
                              {formatMealPortion(
                                participant.quantity,
                                participant.quantity_unit,
                                participant.energy_kcal,
                                locale,
                              )}
                            </span>
                          </div>
                          <div className="weekly-person-detail__reason">
                            {energyReference ? (
                              <p className="muted compact">
                                {copy.mealEnergyReference}: <strong>{energyReference}</strong>
                              </p>
                            ) : null}
                            <MealPlanFitAssessment
                              compact
                              data={{
                                eligible: participant.plan_fit_detail.eligible,
                                status: participant.plan_fit_detail.status,
                                fitScore: participant.plan_fit_detail.fit_score,
                                authorityState: participant.nutrition_plan_authority,
                                activePlanTitles: participant.active_plan_titles,
                                nutrition: participant.nutrition,
                                conflicts: participant.plan_fit_detail.conflicts,
                                safetyIssues: participant.plan_fit_detail.safety_issues,
                                ruleResults: participant.plan_fit_detail.rule_results,
                                guidelineResults:
                                  participant.plan_fit_detail.guideline_results,
                              }}
                            />
                            <small>{copy.nutritionReason}</small>
                            {explanationLabels.length > 0 ? (
                              <ul className="compact-list">
                                {explanationLabels.slice(0, 4).map((message) => (
                                  <li key={message}>{message}</li>
                                ))}
                              </ul>
                            ) : (
                              <p className="muted compact">{copy.noExplanation}</p>
                            )}
                          </div>
                        </article>
                      );
                    })}
                  </div>
                  {adaptationError ? (
                    <div className="error-banner" role="alert">
                      <span>{adaptationError}</span>
                    </div>
                  ) : null}
                  {adaptationResult ? (
                    <section className="weekly-adaptation-panel">
                      <div>
                        <span className="eyebrow">{copy.adaptationTitle}</span>
                        <p className="muted compact">{copy.adaptationHelp}</p>
                      </div>
                      {adaptationResult.proposals.length > 0 ? (
                        <div className="weekly-adaptation-list">
                          {adaptationResult.proposals.map((adaptation) => (
                            <article
                              className="weekly-adaptation-card"
                              key={`${adaptation.operation.recipe_ingredient_id}:${adaptation.operation.replacement_food_item_id}`}
                            >
                              <div className="weekly-adaptation-card__heading">
                                <span className="weekly-transformation-summary__kind">
                                  {adaptationKindLabel(adaptation, locale)}
                                </span>
                                <strong>
                                  {adaptation.operation.source_food_name} →{" "}
                                  {adaptation.operation.replacement_food_name}
                                </strong>
                              </div>
                              <p className="muted compact">
                                {adaptation.plan_improvement_participants > 0
                                  ? copy.planImprovesFor
                                  : copy.preferenceImprovesFor}:{" "}
                                <strong>
                                  {peopleCountLabel(
                                    adaptation.plan_improvement_participants > 0
                                      ? adaptation.plan_improvement_participants
                                      : adaptation.preference_improvement_participants,
                                    locale,
                                  )}
                                </strong>
                              </p>
                              <div className="weekly-adaptation-people">
                                {adaptation.participant_results.map((result) => {
                                  const adaptedPerson = peopleById.get(result.person_id);
                                  const beforeEnergy =
                                    result.before_fit.candidate.nutrition.energy_kcal;
                                  const afterEnergy =
                                    result.after_fit.candidate.nutrition.energy_kcal;
                                  return (
                                    <div key={result.person_id}>
                                      <strong>
                                        {adaptedPerson
                                          ? displayName(adaptedPerson)
                                          : result.person_id}
                                      </strong>
                                      <span>
                                        {copy.beforeAfter}:{" "}
                                        {planFitStatusLabel(
                                          result.before_fit.status,
                                          locale,
                                        )}{" "}
                                        →{" "}
                                        {planFitStatusLabel(
                                          result.after_fit.status,
                                          locale,
                                        )}
                                      </span>
                                      <small>
                                        {formatNutritionValue(
                                          beforeEnergy,
                                          "kcal",
                                          locale,
                                        )}{" "}
                                        →{" "}
                                        {formatNutritionValue(
                                          afterEnergy,
                                          "kcal",
                                          locale,
                                        )}
                                      </small>
                                    </div>
                                  );
                                })}
                              </div>
                              <div className="weekly-adaptation-card__actions">
                                <button
                                  className="button primary"
                                  disabled={
                                    busy ||
                                    decisionBusy !== null ||
                                    adaptationChoiceBusy !== null
                                  }
                                  onClick={() => void useAdaptation(adaptation)}
                                  type="button"
                                >
                                  {adaptationChoiceBusy === selectedChoice.slot_key
                                    ? copy.usingAdaptation
                                    : copy.useAdaptation}
                                </button>
                              </div>
                            </article>
                          ))}
                        </div>
                      ) : (
                        <div className="weekly-adaptation-limitations">
                          <p className="muted compact">{copy.noAdaptation}</p>
                          {adaptationResult.limitations
                            .map((limitation) =>
                              transformationLimitationLabel(limitation, locale),
                            )
                            .filter((message): message is string => message !== null)
                            .map((message) => (
                              <p className="muted compact" key={message}>
                                {message}
                              </p>
                            ))}
                        </div>
                      )}
                    </section>
                  ) : null}
                  <div className="meal-plan-editor__actions">
                    <button
                      className="button ghost"
                      disabled={
                        busy ||
                        decisionBusy !== null ||
                        adaptationBusy ||
                        adaptationChoiceBusy !== null
                      }
                      onClick={() => void rejectSelectedChoice()}
                      type="button"
                    >
                      {decisionBusy === "reject" ? copy.rejecting : copy.rejectRecipe}
                    </button>
                  </div>
                </>
              ) : selectedSkippedReason ? (
                <div className="family-meals-empty-day">
                  <strong>{copy.pending}</strong>
                  <p>{selectedSkippedReason}</p>
                  {selectedMealType === "lunch" && !isWeekendDate(selectedDate) ? (
                    <p className="muted compact">{copy.leftoversNotice}</p>
                  ) : null}
                </div>
              ) : (
                <div className="family-meals-empty-day">{copy.empty}</div>
              )}
            </section>
          ) : null}
        </>
      )}
    </section>
  );
}
