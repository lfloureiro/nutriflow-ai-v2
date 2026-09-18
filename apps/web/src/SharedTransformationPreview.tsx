import { useState } from "react";

import { ApiError } from "./api/client";
import {
  planSharedMealTransformation,
  proposeSharedMealTransformations,
} from "./api/sharedMealTransformationClient";
import type {
  SharedMealTransformationPlan,
  SharedMealTransformationResult,
} from "./api/sharedMealTransformationTypes";
import type { SharedRecommendationOption } from "./api/sharedRecommendationTypes";
import type { PlanningMealType } from "./api/types";
import { useI18n } from "./i18n";

const COPY = {
  "pt-PT": {
    preview: "Ver adaptação",
    hide: "Ocultar adaptação",
    loading: "A avaliar adaptação…",
    title: "Adaptação da receita",
    planAdapted: "Adaptada ao plano",
    preferenceVariant: "Variante por preferência",
    replace: "Substituir",
    planImprovement: "melhoria suportada pelo plano",
    planImprovements: "melhorias suportadas pelo plano",
    preferenceImprovement: "preferência melhorada",
    preferenceImprovements: "preferências melhoradas",
    none: "Não foi encontrada uma adaptação segura que melhore esta receita para o grupo.",
    note: "A aplicação volta a validar plano, segurança e preferências antes de criar a refeição.",
    add: "Adicionar adaptação ao plano",
    adding: "A adicionar adaptação…",
    error: "Não foi possível avaliar ou aplicar a adaptação.",
  },
  en: {
    preview: "Preview adaptation",
    hide: "Hide adaptation",
    loading: "Evaluating adaptation…",
    title: "Recipe adaptation",
    planAdapted: "Adapted to plan",
    preferenceVariant: "Preference variant",
    replace: "Replace",
    planImprovement: "plan-backed improvement",
    planImprovements: "plan-backed improvements",
    preferenceImprovement: "preference improvement",
    preferenceImprovements: "preference improvements",
    none: "No safe adaptation was found that improves this recipe for the group.",
    note: "Applying revalidates plan, safety and preferences before creating the meal.",
    add: "Add adaptation to plan",
    adding: "Adding adaptation…",
    error: "Could not evaluate or apply this adaptation.",
  },
} as const;

function errorText(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return `${error.message} (HTTP ${error.status})`;
  if (error instanceof Error) return error.message;
  return fallback;
}

export default function SharedTransformationPreview({
  familyId,
  mealType,
  location,
  mealPlanned,
  onPlanned,
  onPlanningChange,
  option,
  planning,
  planningDate,
  recipeId,
  scheduledAt,
}: {
  familyId: string;
  location: string | null;
  mealPlanned: boolean;
  mealType: PlanningMealType;
  onPlanned: (plan: SharedMealTransformationPlan) => void;
  onPlanningChange: (busy: boolean) => void;
  option: SharedRecommendationOption;
  planning: boolean;
  planningDate: string;
  recipeId: string | null;
  scheduledAt: string;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [result, setResult] = useState<SharedMealTransformationResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!recipeId || option.candidate_kind !== "recipe") return null;
  const resolvedRecipeId: string = recipeId;

  const participants = option.participants.map((participant) => ({
    person_id: participant.person_id,
    daily_nutrition_state_id: null,
    quantity: participant.quantity,
    quantity_unit: participant.quantity_unit,
  }));

  async function togglePreview() {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (result) return;

    setBusy(true);
    setError(null);
    try {
      const response = await proposeSharedMealTransformations(familyId, {
        planning_date: planningDate,
        meal_type: mealType,
        recipe_id: resolvedRecipeId,
        participants,
        max_proposals: 3,
      });
      setResult(response);
    } catch (caught: unknown) {
      setError(errorText(caught, copy.error));
    } finally {
      setBusy(false);
    }
  }


  async function applyProposal(
    proposal: SharedMealTransformationResult["proposals"][number],
  ) {
    onPlanningChange(true);
    setError(null);
    try {
      const planned = await planSharedMealTransformation(familyId, {
        planning_date: planningDate,
        meal_type: mealType,
        recipe_id: resolvedRecipeId,
        participants,
        recipe_ingredient_id: proposal.operation.recipe_ingredient_id,
        replacement_food_item_id: proposal.operation.replacement_food_item_id,
        scheduled_at: scheduledAt,
        title: option.candidate_name,
        location,
      });
      onPlanned(planned);
    } catch (caught: unknown) {
      setError(errorText(caught, copy.error));
    } finally {
      onPlanningChange(false);
    }
  }

  return (
    <div className="shared-transformation-preview">
      <button
        className="button ghost"
        disabled={busy || planning}
        onClick={() => void togglePreview()}
        type="button"
      >
        {busy ? copy.loading : open ? copy.hide : copy.preview}
      </button>

      {open ? (
        <div className="shared-transformation-preview__content">
          <div>
            <strong>{copy.title}</strong>
            <small>{copy.note}</small>
          </div>

          {error ? <span className="shared-transformation-preview__error">{error}</span> : null}

          {result && result.proposals.length === 0 ? (
            <span className="muted">{copy.none}</span>
          ) : null}

          {result?.proposals.map((proposal) => {
            const planCount = proposal.plan_improvement_participants;
            const preferenceCount = proposal.preference_improvement_participants;
            return (
              <article
                className="shared-transformation-proposal"
                key={`${proposal.operation.recipe_ingredient_id}:${proposal.operation.replacement_food_item_id}`}
              >
                <div className="shared-transformation-proposal__heading">
                  <span
                    className={`shared-transformation-kind shared-transformation-kind--${proposal.kind}`}
                  >
                    {proposal.kind === "plan_adapted"
                      ? copy.planAdapted
                      : copy.preferenceVariant}
                  </span>
                  <strong>
                    {copy.replace} {proposal.operation.source_food_name} →{" "}
                    {proposal.operation.replacement_food_name}
                  </strong>
                </div>
                <small>
                  {proposal.kind === "plan_adapted"
                    ? `${planCount} ${planCount === 1 ? copy.planImprovement : copy.planImprovements}`
                    : `${preferenceCount} ${preferenceCount === 1 ? copy.preferenceImprovement : copy.preferenceImprovements}`}
                </small>
                {!mealPlanned ? (
                  <button
                    className="button primary"
                    disabled={planning}
                    onClick={() => void applyProposal(proposal)}
                    type="button"
                  >
                    {planning ? copy.adding : copy.add}
                  </button>
                ) : null}
              </article>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
