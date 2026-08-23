import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  ApiError,
  cancelMealPlanEntry,
  createMealPlanEntry,
  getFamilyMealPlan,
  listFamilyPersons,
  listFamilyRecipes,
  updateMealPlanEntry,
} from "./api/client";
import type {
  FamilyMealPlan,
  MealPlanEntry,
  MealPlanParticipantWrite,
  MealType,
} from "./api/mealPlanTypes";
import type { Recipe } from "./api/recipeTypes";
import type { Person } from "./api/types";
import { useI18n, type Locale } from "./i18n";
import MealConsumptionControls from "./MealConsumptionControls";
import MealPlanner from "./MealPlanner";
import { localDateValue } from "./planning";

export type FamilyMealsMode = "today" | "week" | "recommend";

const DEFAULT_TIMES: Record<MealType, string> = {
  breakfast: "08:30",
  lunch: "13:00",
  snack: "17:00",
  dinner: "20:00",
};

const COPY = {
  "pt-PT": {
    title: "Plano alimentar da família",
    help: "Planeia os quatro tempos do dia. Adiciona, altera ou remove refeições e ajusta as porções por pessoa.",
    today: "Hoje",
    week: "Semana",
    recommend: "Recomendar",
    navigation: "Navegação do plano alimentar",
    loading: "A carregar plano…",
    add: "Adicionar",
    edit: "Alterar",
    empty: "Sem refeição planeada",
    recipe: "Receita",
    chooseRecipe: "Escolher receita",
    time: "Hora",
    participants: "Pessoas e porções",
    defaultPortion: "porção padrão",
    quantity: "Quantidade",
    unit: "Unidade",
    location: "Local",
    save: "Guardar no plano",
    saving: "A guardar…",
    remove: "Remover do plano",
    cancel: "Cancelar",
    confirmRemove: "Remover esta refeição do planeamento? O registo fica preservado como cancelado.",
    noRecipes: "Ainda não existem receitas ativas. Cria primeiro uma receita em Casa → Receitas.",
    noPeople: "Não existem pessoas disponíveis nesta família.",
    planned: "Planeada",
    completed: "Concluída",
    prepared: "Preparada",
    served: "Servida",
    locked: "Já não pode ser alterada no planeamento",
    error: "Não foi possível concluir a operação",
  },
  en: {
    title: "Family meal plan",
    help: "Plan the four daily meal slots. Add, change or remove meals and adjust each person's portion.",
    today: "Today",
    week: "Week",
    recommend: "Recommend",
    navigation: "Meal plan navigation",
    loading: "Loading meal plan…",
    add: "Add",
    edit: "Edit",
    empty: "No meal planned",
    recipe: "Recipe",
    chooseRecipe: "Choose recipe",
    time: "Time",
    participants: "People and portions",
    defaultPortion: "default portion",
    quantity: "Quantity",
    unit: "Unit",
    location: "Location",
    save: "Save to plan",
    saving: "Saving…",
    remove: "Remove from plan",
    cancel: "Cancel",
    confirmRemove: "Remove this meal from the plan? The record remains preserved as cancelled.",
    noRecipes: "There are no active recipes yet. Create one in Home base → Recipes first.",
    noPeople: "There are no people available in this family.",
    planned: "Planned",
    completed: "Completed",
    prepared: "Prepared",
    served: "Served",
    locked: "This meal can no longer be changed in planning",
    error: "The operation could not be completed",
  },
} as const;

type ParticipantDraft = {
  personId: string;
  selected: boolean;
  quantity: string;
  unit: string;
};

type EditTarget = {
  date: string;
  mealType: MealType;
  entry: MealPlanEntry | null;
};

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.message} (HTTP ${error.status})`;
  }
  return error instanceof Error ? error.message : String(error);
}

export function startOfWeekDate(isoDate: string): string {
  const value = new Date(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(value.getTime())) {
    throw new Error("Invalid ISO calendar date.");
  }
  const weekday = value.getUTCDay();
  const offset = weekday === 0 ? -6 : 1 - weekday;
  value.setUTCDate(value.getUTCDate() + offset);
  return value.toISOString().slice(0, 10);
}

function formatDate(value: string, locale: Locale): string {
  return new Intl.DateTimeFormat(locale, {
    weekday: "long",
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function mealLabel(mealType: MealType, locale: Locale): string {
  const labels: Record<Locale, Record<MealType, string>> = {
    "pt-PT": {
      breakfast: "Pequeno-almoço",
      lunch: "Almoço",
      snack: "Lanche",
      dinner: "Jantar",
    },
    en: { breakfast: "Breakfast", lunch: "Lunch", snack: "Snack", dinner: "Dinner" },
  };
  return labels[locale][mealType];
}

function displayName(person: Person): string {
  return [person.first_name, person.last_name].filter(Boolean).join(" ");
}

function entryParticipants(entry: MealPlanEntry): string {
  return entry.participants
    .map((participant) => [participant.first_name, participant.last_name].filter(Boolean).join(" "))
    .join(" · ");
}

function statusLabel(status: string, locale: Locale): string {
  const copy = COPY[locale];
  if (status === "planned") return copy.planned;
  if (status === "prepared") return copy.prepared;
  if (status === "served") return copy.served;
  if (status === "completed") return copy.completed;
  return status;
}

function MealEditForm({
  target,
  familyId,
  recipes,
  people,
  onDone,
}: {
  target: EditTarget;
  familyId: string;
  recipes: Recipe[];
  people: Person[];
  onDone: () => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const entry = target.entry;
  const [recipeId, setRecipeId] = useState(entry?.recipe_id ?? recipes[0]?.id ?? "");
  const [localTime, setLocalTime] = useState(
    entry?.local_time.slice(0, 5) ?? DEFAULT_TIMES[target.mealType],
  );
  const [location, setLocation] = useState(entry?.location ?? "Casa");
  const [participants, setParticipants] = useState<ParticipantDraft[]>(() =>
    people.map((person) => {
      const existing = entry?.participants.find(
        (participant) => participant.person_id === person.id,
      );
      return {
        personId: person.id,
        selected: entry ? Boolean(existing) : true,
        quantity: existing?.quantity ?? "",
        unit: existing?.unit ?? "g",
      };
    }),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function patchParticipant(personId: string, patch: Partial<ParticipantDraft>) {
    setParticipants((current) =>
      current.map((participant) =>
        participant.personId === personId ? { ...participant, ...patch } : participant,
      ),
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const selected = participants.filter((participant) => participant.selected);
    if (!recipeId || selected.length === 0) {
      setError(!recipeId ? copy.chooseRecipe : copy.noPeople);
      return;
    }
    const participantPayload: MealPlanParticipantWrite[] = selected.map((participant) => ({
      person_id: participant.personId,
      ...(participant.quantity.trim()
        ? { quantity: participant.quantity.trim().replace(",", "."), unit: participant.unit }
        : {}),
    }));
    const payload = {
      date: target.date,
      meal_type: target.mealType,
      local_time: localTime,
      recipe_id: recipeId,
      participants: participantPayload,
      location: location.trim() || null,
    };
    setBusy(true);
    try {
      if (entry) {
        await updateMealPlanEntry(familyId, entry.id, payload);
      } else {
        await createMealPlanEntry(familyId, payload);
      }
      onDone();
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  async function removeEntry() {
    if (!entry || !window.confirm(copy.confirmRemove)) return;
    setBusy(true);
    setError(null);
    try {
      await cancelMealPlanEntry(familyId, entry.id);
      onDone();
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="meal-plan-editor">
      <div className="meal-plan-editor__heading">
        <div>
          <span className="eyebrow">{formatDate(target.date, locale)}</span>
          <h2>{mealLabel(target.mealType, locale)}</h2>
        </div>
        <button className="button ghost" onClick={onDone} type="button">
          {copy.cancel}
        </button>
      </div>
      {error ? (
        <div className="error-banner" role="alert">
          <strong>{copy.error}</strong><span>{error}</span>
        </div>
      ) : null}
      {recipes.length === 0 ? (
        <div className="family-meals-empty-day">{copy.noRecipes}</div>
      ) : null}
      <form className="meal-plan-form" onSubmit={submit}>
        <div className="meal-plan-form-grid">
          <label className="field meal-plan-wide">
            <span>{copy.recipe}</span>
            <select value={recipeId} onChange={(event) => setRecipeId(event.target.value)}>
              <option value="">{copy.chooseRecipe}</option>
              {recipes.map((recipe) => (
                <option key={recipe.id} value={recipe.id}>{recipe.name}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>{copy.time}</span>
            <input
              type="time"
              value={localTime}
              onChange={(event) => setLocalTime(event.target.value)}
            />
          </label>
          <label className="field">
            <span>{copy.location}</span>
            <input value={location} onChange={(event) => setLocation(event.target.value)} />
          </label>
        </div>
        <div className="meal-plan-participants">
          <h3>{copy.participants}</h3>
          {participants.map((participant) => {
            const person = people.find((candidate) => candidate.id === participant.personId);
            if (!person) return null;
            return (
              <div className="meal-plan-person" key={participant.personId}>
                <label className="meal-plan-person__check">
                  <input
                    checked={participant.selected}
                    onChange={(event) =>
                      patchParticipant(participant.personId, { selected: event.target.checked })
                    }
                    type="checkbox"
                  />
                  <strong>{displayName(person)}</strong>
                </label>
                <label className="field">
                  <span>{copy.quantity} <small>({copy.defaultPortion})</small></span>
                  <input
                    disabled={!participant.selected}
                    inputMode="decimal"
                    placeholder="—"
                    value={participant.quantity}
                    onChange={(event) =>
                      patchParticipant(participant.personId, { quantity: event.target.value })
                    }
                  />
                </label>
                <label className="field">
                  <span>{copy.unit}</span>
                  <select
                    disabled={!participant.selected || !participant.quantity.trim()}
                    value={participant.unit}
                    onChange={(event) =>
                      patchParticipant(participant.personId, { unit: event.target.value })
                    }
                  >
                    <option value="g">g</option>
                    <option value="kg">kg</option>
                    <option value="ml">ml</option>
                    <option value="l">l</option>
                    <option value="serving">dose</option>
                    <option value="recipe">receita</option>
                  </select>
                </label>
              </div>
            );
          })}
        </div>
        <div className="meal-plan-editor__actions">
          <button
            className="button primary"
            disabled={busy || recipes.length === 0}
            type="submit"
          >
            {busy ? copy.saving : copy.save}
          </button>
          {entry ? (
            <button className="button ghost" disabled={busy} onClick={removeEntry} type="button">
              {copy.remove}
            </button>
          ) : null}
        </div>
      </form>
    </section>
  );
}

export default function FamilyMealsScreen({
  familyId,
  referenceDate,
  mode,
  onModeChange,
  onDataChanged,
}: {
  familyId: string;
  referenceDate?: string;
  mode: FamilyMealsMode;
  onModeChange: (mode: FamilyMealsMode) => void;
  onDataChanged?: () => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [plan, setPlan] = useState<FamilyMealPlan | null>(null);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [editing, setEditing] = useState<EditTarget | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  const request = useMemo(() => {
    if (mode === "recommend") return null;
    if (mode === "today") return { startDate: referenceDate, days: 1 };
    return {
      startDate: referenceDate ? startOfWeekDate(referenceDate) : undefined,
      days: 7,
    };
  }, [mode, referenceDate]);

  useEffect(() => {
    if (!request) return;
    let cancelled = false;
    setBusy(true);
    setError(null);
    void Promise.all([
      getFamilyMealPlan(familyId, request.startDate, request.days),
      listFamilyRecipes(familyId),
      listFamilyPersons(familyId),
    ])
      .then(([planResult, recipeResult, peopleResult]) => {
        if (!cancelled) {
          setPlan(planResult);
          setRecipes(recipeResult);
          setPeople(peopleResult);
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setPlan(null);
          setError(errorText(caught));
        }
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [familyId, request, revision]);

  function refreshPlan() {
    setRevision((current) => current + 1);
    onDataChanged?.();
  }

  function closeEditor() {
    setEditing(null);
    refreshPlan();
  }

  const consumptionDate = referenceDate ?? localDateValue();

  return (
    <div className="family-meals-screen">
      <header className="screen-header compact-screen-header family-meals-header">
        <div>
          <span className="eyebrow">Plano</span>
          <h1>{copy.title}</h1>
          <p>{copy.help}</p>
        </div>
      </header>
      <nav className="secondary-tabs family-meals-tabs" aria-label={copy.navigation}>
        <button
          className={mode === "today" ? "active" : ""}
          onClick={() => {
            setEditing(null);
            onModeChange("today");
          }}
          type="button"
        >
          {copy.today}
        </button>
        <button
          className={mode === "week" ? "active" : ""}
          onClick={() => {
            setEditing(null);
            onModeChange("week");
          }}
          type="button"
        >
          {copy.week}
        </button>
        <button
          className={mode === "recommend" ? "active" : ""}
          onClick={() => {
            setEditing(null);
            onModeChange("recommend");
          }}
          type="button"
        >
          {copy.recommend}
        </button>
      </nav>

      {mode === "recommend" ? <MealPlanner familyId={familyId} /> : null}
      {mode !== "recommend" && error ? (
        <div className="error-banner" role="alert">
          <strong>{copy.error}</strong><span>{error}</span>
        </div>
      ) : null}
      {mode !== "recommend" && busy ? (
        <div className="shell-loading" role="status">{copy.loading}</div>
      ) : null}

      {mode !== "recommend" && !busy && plan ? (
        editing ? (
          <MealEditForm
            familyId={familyId}
            onDone={closeEditor}
            people={people}
            recipes={recipes}
            target={editing}
          />
        ) : (
          <div className={`meal-plan-days ${mode === "week" ? "week" : "today"}`}>
            {plan.days.map((day) => (
              <section className="meal-plan-day" key={day.date}>
                <div className="family-meals-day__heading">
                  <h2>{formatDate(day.date, locale)}</h2>
                </div>
                <div className="meal-plan-slots">
                  {day.slots.map((slot) => (
                    <div className="meal-plan-slot" key={slot.meal_type}>
                      <div className="meal-plan-slot__heading">
                        <strong>{mealLabel(slot.meal_type, locale)}</strong>
                        <button
                          className="button ghost"
                          onClick={() =>
                            setEditing({ date: day.date, mealType: slot.meal_type, entry: null })
                          }
                          type="button"
                        >
                          + {copy.add}
                        </button>
                      </div>
                      {slot.meals.length === 0 ? (
                        <div className="meal-plan-empty">{copy.empty}</div>
                      ) : (
                        <div className="meal-plan-entry-list">
                          {slot.meals.map((entry) => (
                            <div className="meal-plan-entry-group" key={entry.id}>
                              <button
                                className="meal-plan-entry"
                                disabled={entry.status !== "planned"}
                                onClick={() =>
                                  setEditing({
                                    date: day.date,
                                    mealType: slot.meal_type,
                                    entry,
                                  })
                                }
                                type="button"
                              >
                                <span className="meal-plan-entry__time">
                                  {entry.local_time.slice(0, 5)}
                                </span>
                                <span className="meal-plan-entry__body">
                                  <strong>
                                    {entry.recipe_name ??
                                      entry.title ??
                                      mealLabel(slot.meal_type, locale)}
                                  </strong>
                                  <small>
                                    {entryParticipants(entry) || copy.noPeople}
                                    {entry.location ? ` · ${entry.location}` : ""}
                                  </small>
                                </span>
                                <span className="meal-plan-entry__status">
                                  {statusLabel(entry.status, locale)}
                                  {entry.status === "planned"
                                    ? ` · ${copy.edit}`
                                    : ` · ${copy.locked}`}
                                </span>
                              </button>
                              {day.date <= consumptionDate ? (
                                <div className="meal-consumption-list">
                                  {entry.participants.map((participant) => (
                                    <MealConsumptionControls
                                      entry={entry}
                                      familyId={familyId}
                                      key={participant.person_id}
                                      onUpdated={refreshPlan}
                                      participant={participant}
                                    />
                                  ))}
                                </div>
                              ) : null}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )
      ) : null}
    </div>
  );
}
