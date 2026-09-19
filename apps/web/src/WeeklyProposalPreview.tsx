import { useEffect, useMemo, useState } from "react";

import { ApiError, cancelMealPlanEntry, getFamilyMealPlan } from "./api/client";
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
  SharedWeeklyPlanProposal,
  SharedWeeklyPlanSkippedSlot,
  SharedWeeklyPlanProposalRequest,
  SharedWeeklyPlanRequest,
  SharedWeeklyPlanningSlotRequest,
} from "./api/weeklyPlanningTypes";
import type { Person } from "./api/types";
import { useI18n, type Locale } from "./i18n";
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
    planTarget: "Alvo do plano",
    observed: "Nesta porção",
    adaptToPlan: "Adaptar ao plano",
    adaptingToPlan: "A procurar adaptações…",
    adaptationTitle: "Sugestões de adaptação",
    adaptationHelp: "Substituições avaliadas contra o plano e as preferências da família. Nenhuma alteração é aplicada automaticamente.",
    noAdaptation: "Não foram encontradas substituições seguras configuradas que melhorem esta receita.",
    planImprovesFor: "Melhora o plano para",
    peopleLabel: "pessoa(s)",
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
    planTarget: "Plan target",
    observed: "In this portion",
    adaptToPlan: "Adapt to plan",
    adaptingToPlan: "Finding adaptations…",
    adaptationTitle: "Adaptation suggestions",
    adaptationHelp: "Substitutions evaluated against the plan and Family preferences. No change is applied automatically.",
    noAdaptation: "No configured safe substitutions were found that improve this recipe.",
    planImprovesFor: "Improves the plan for",
    peopleLabel: "person(s)",
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
  status: SharedWeeklyPlanChoice["participants"][number]["plan_fit_status"],
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
  const selectedSlotKey =
    selectedDate && selectedMealType ? slotKey(selectedDate, selectedMealType) : null;
  const selectedSkippedReason = selectedSlotKey ? skippedSlots[selectedSlotKey] ?? null : null;

  async function generateProposal(
    rejectedOverride: RejectedBySlot = rejectedBySlot,
    resetSelection = true,
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
    setRejectedBySlot(next);
    setDecisionBusy("reject");
    setError(null);
    setNotice(null);
    try {
      await generateProposal(next, false);
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
              disabled={busy || decisionBusy !== null || proposalRequest === null}
              onClick={() => void applyWeek()}
              type="button"
            >
              {decisionBusy === "apply" ? copy.applyingWeek : copy.applyWeek}
            </button>
          ) : null}
          <button
            className={proposal?.selected_plan ? "button ghost" : "button primary"}
            disabled={busy || decisionBusy !== null || people.length < 2 || !plan}
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
                            <small>{copy.nutritionPlan}</small>
                            <p className="muted compact">
                              <strong>
                                {nutritionPlanAuthorityLabel(
                                  participant.nutrition_plan_authority,
                                  locale,
                                )}
                              </strong>
                              {participant.active_plan_titles.length > 0
                                ? ` · ${participant.active_plan_titles.join(", ")}`
                                : ""}
                            </p>
                            <p className="muted compact">
                              {copy.mealPlanFit}:{" "}
                              {planFitStatusLabel(participant.plan_fit_status, locale)}
                              {participant.plan_fit_score !== null
                                ? ` · ${participant.plan_fit_score}`
                                : ""}
                            </p>
                            {energyReference ? (
                              <p className="muted compact">
                                {copy.mealEnergyReference}: {energyReference}
                              </p>
                            ) : null}
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
                  <div className="meal-plan-editor__actions">
                    <button
                      className="button ghost"
                      disabled={busy || decisionBusy !== null}
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
