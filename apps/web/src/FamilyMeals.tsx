import {useUnsavedChanges} from "./useUnsavedChanges";
import PersonAvatar from "./ui/PersonAvatar";
import ContextDrawer from "./ui/ContextDrawer";
import Icon from "./ui/Icon";
import NextMealHero, {type HeroSuggestedMeal} from "./NextMealBanner";
import {searchText} from "./recipeBrowsing";
import {listRecipeReviews,type ReviewRecipe} from "./api/dietaryReviewClient";
import SavedMealChanges from "./SavedMealChanges";
import { lazy, Suspense, useEffect, useMemo, useRef, useState, type FormEvent } from "react";

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
const MealPlanner = lazy(() => import("./MealPlanner"));
import { localDateValue } from "./planning";
const WeeklyProposalPreview = lazy(() => import("./WeeklyProposalPreview"));
const PlanningJourney = lazy(() => import("./PlanningJourney"));

export type FamilyMealsMode = "prepare" | "today" | "week" | "recommend";

const DEFAULT_TIMES: Record<MealType, string> = {
  breakfast: "08:30",
  lunch: "13:00",
  snack: "17:00",
  dinner: "20:00",
};

const COPY = {
  "pt-PT": {
    title: "A semana tem lugar para todos.",
    help: "Escolhe, ajusta e acompanha as refeições da família, com o cuidado certo para cada pessoa.",
    today: "Hoje",
    week: "Semana",
    recommend: "Recomendar",
    navigation: "Navegação do plano alimentar",
    dateNavigation: "Navegação por datas",
    previousDay: "‹ Dia anterior",
    nextDay: "Dia seguinte ›",
    previousWeek: "‹ Semana anterior",
    nextWeek: "Semana seguinte ›",
    backToToday: "Hoje",
    backToThisWeek: "Esta semana",
    loading: "A carregar plano…",
    add: "Adicionar",
    edit: "Alterar",
    view: "Ver",
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
    noRecipes: "Não existem receitas disponíveis para este tempo de refeição.",
    noPeople: "Não existem pessoas disponíveis nesta família.",
    planned: "Planeada",
    completed: "Concluída",
    prepared: "Preparada",
    served: "Servida",
    locked: "Já não pode ser alterada no planeamento",
    transformedLocked: "Esta refeição foi adaptada automaticamente. Para preservar a transformação e a sua proveniência, o editor normal é apenas de leitura.",
    planAdapted: "Adaptada ao plano",
    preferenceVariant: "Variante por preferência",
    replace: "Substituição",
    error: "Não foi possível concluir a operação",
  },
  en: {
    title: "A week with room for everyone.",
    help: "Plan the four daily meal slots. Add, change or remove meals and adjust each person's portion.",
    today: "Today",
    week: "Week",
    recommend: "Recommend",
    navigation: "Meal plan navigation",
    dateNavigation: "Date navigation",
    previousDay: "‹ Previous day",
    nextDay: "Next day ›",
    previousWeek: "‹ Previous week",
    nextWeek: "Next week ›",
    backToToday: "Today",
    backToThisWeek: "This week",
    loading: "Loading meal plan…",
    add: "Add",
    edit: "Edit",
    view: "View",
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
    noRecipes: "There are no recipes available for this meal slot.",
    noPeople: "There are no people available in this family.",
    planned: "Planned",
    completed: "Completed",
    prepared: "Prepared",
    served: "Served",
    locked: "This meal can no longer be changed in planning",
    transformedLocked: "This meal was automatically adapted. To preserve the transformation and its provenance, the standard editor is read-only.",
    planAdapted: "Adapted to plan",
    preferenceVariant: "Preference variant",
    replace: "Replacement",
    error: "The operation could not be completed",
  },
} as const;

export type AttendanceDecision = "present" | "absent" | "unconfirmed";

export type ParticipantDraft = {
  personId: string;
  attendance: AttendanceDecision;
  quantity: string;
  unit: string;
};

/** Copy decisions only. Inherited quantities or units would be unsafe for another meal. */
export function copyAttendanceSelection(
  current: ParticipantDraft[], previousAttendeeIds: readonly string[],
): ParticipantDraft[] {
  const previous = new Set(previousAttendeeIds);
  return current.map(person => ({...person, attendance: previous.has(person.personId) ? "present" : "absent"}));
}

type EditTarget = {
  date: string;
  mealType: MealType;
  entry: MealPlanEntry | null;
};

export function mealPlanErrorText(error: unknown, locale: Locale): string {
  const message = error instanceof Error ? error.message : String(error);
  const conflict = message.match(/^Recipe conflicts with active attendee restrictions: (.+)\. Choose and validate a compatible variant before saving\.$/);
  if (locale === "pt-PT" && conflict) return `A receita tem ingredientes incompatíveis com as restrições dos presentes: ${conflict[1]}. Escolhe e valida uma variante compatível antes de guardar.`;
  if (error instanceof ApiError) {
    return `${error.message} (HTTP ${error.status})`;
  }
  return error instanceof Error ? error.message : String(error);
}

export function addPlanDays(isoDate: string, days: number): string {
  const value = new Date(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(value.getTime())) {
    throw new Error("Invalid ISO calendar date.");
  }
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
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

export function recipesForMealType(recipes: Recipe[], mealType: MealType): Recipe[] {
  return recipes.filter((recipe) => recipe.suitable_meal_types.includes(mealType));
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

function transformationLabel(
  kind: "plan_adapted" | "preference_variant",
  locale: Locale,
): string {
  return kind === "plan_adapted" ? COPY[locale].planAdapted : COPY[locale].preferenceVariant;
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
  attendanceSources,
  registerClose,
}: {
  target: EditTarget;
  familyId: string;
  recipes: Recipe[];
  people: Person[];
  onDone: (changed?: boolean) => void;
  attendanceSources: {date:string;entry:MealPlanEntry}[];
  registerClose?: (close: () => void) => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const entry = target.entry;
  const eligibleRecipes = useMemo(
    () => recipesForMealType(recipes, target.mealType),
    [recipes, target.mealType],
  );
  const [recipeId, setRecipeId] = useState(
    entry?.recipe_id ?? eligibleRecipes[0]?.id ?? "",
  );
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
        attendance: entry ? (existing ? "present" : "absent") : "unconfirmed",
        quantity: existing?.quantity ?? "",
        unit: existing?.unit ?? "g",
      };
    }),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attendanceSource,setAttendanceSource] = useState("");

  const [recipeQuery,setRecipeQuery]=useState("");
  const guard=useUnsavedChanges({recipeId,localTime,location,participants},locale==="pt-PT"?"Tens alterações nesta refeição por guardar. Sair e descartá-las?":"You have unsaved meal changes. Leave and discard them?");
  const closeEditor=()=>{if(!busy&&guard.confirmDiscard())onDone(false);};
  useEffect(() => { registerClose?.(closeEditor); });
  const present=participants.filter(participant=>participant.attendance==="present");
  const unconfirmed=participants.filter(participant=>participant.attendance==="unconfirmed");
  const selectedRecipe=eligibleRecipes.find(recipe=>recipe.id===recipeId);
  const matchingRecipes=eligibleRecipes.filter(recipe=>recipe.id===recipeId||searchText(recipe.name).includes(searchText(recipeQuery)));
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
    const selected = participants.filter((participant) => participant.attendance === "present");
    if (unconfirmed.length > 0) {
      setError(locale==="pt-PT"?"Confirma a presença ou ausência de cada pessoa antes de guardar.":"Confirm attendance or absence for each person before saving.");
      return;
    }
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
        await updateMealPlanEntry(familyId, entry.id, {...payload,expected_updated_at:entry.updated_at});
      } else {
        await createMealPlanEntry(familyId, payload);
      }
      guard.markSaved();onDone(true);
    } catch (caught: unknown) {
      setError(mealPlanErrorText(caught, locale));
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
      guard.markSaved();onDone(true);
    } catch (caught: unknown) {
      setError(mealPlanErrorText(caught, locale));
    } finally {
      setBusy(false);
    }
  }

  if (entry && entry.transformations.length > 0) {
    return (
      <section className="meal-plan-editor">
        <div className="meal-plan-editor__heading">
          <div>
            <span className="eyebrow">{formatDate(target.date, locale)}</span>
            <h2>{mealLabel(target.mealType, locale)}</h2>
          </div>
          <button className="button ghost" onClick={closeEditor} type="button">
            {copy.cancel}
          </button>
        </div>
        {error ? (
          <div className="error-banner" role="alert">
            <strong>{copy.error}</strong><span>{error}</span>
          </div>
        ) : null}
        <div className="meal-plan-transformation-detail">
          <p>{copy.transformedLocked}</p>
          {entry.transformations.map((transformation) => (
            <div className="meal-plan-transformation-operation" key={transformation.id}>
              <span
                className={`meal-plan-transformation-badge meal-plan-transformation-badge--${transformation.transformation_kind}`}
              >
                {transformationLabel(transformation.transformation_kind, locale)}
              </span>
              <strong>
                {copy.replace}: {transformation.source_food_name} →{" "}
                {transformation.replacement_food_name}
              </strong>
            </div>
          ))}
        </div>
        <div className="meal-plan-editor__actions">
          <button className="button ghost" disabled={busy} onClick={removeEntry} type="button">
            {copy.remove}
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="meal-plan-editor">
      <div className="meal-plan-editor__heading">
        <div>
          <span className="eyebrow">{formatDate(target.date, locale)}</span>
          <h2>{mealLabel(target.mealType, locale)}</h2>
        </div>
        <button className="button ghost" onClick={closeEditor} type="button">
          {copy.cancel}
        </button>
      </div>
      {error ? (
        <div className="error-banner" role="alert">
          <strong>{copy.error}</strong><span>{error}</span>
        </div>
      ) : null}
      {eligibleRecipes.length === 0 ? (
        <div className="family-meals-empty-day">{copy.noRecipes}</div>
      ) : null}
      {guard.dirty&&<p className="nf-draft-state" role="status">{locale==="pt-PT"?"Alterações por guardar":"Unsaved changes"}</p>}
      <form className="meal-plan-form" onSubmit={submit}><fieldset className="nf-form-lock" disabled={busy}>
        <label className="field"><span>{locale==="pt-PT"?"Procurar receita para esta refeição":"Find recipe for this meal"}</span><input type="search" value={recipeQuery} onChange={event=>setRecipeQuery(event.target.value)} placeholder={locale==="pt-PT"?"Nome da receita…":"Recipe name…"}/></label>
        <div className="meal-plan-form-grid">
          <label className="field meal-plan-wide">
            <span>{copy.recipe}</span>
            <select value={recipeId} onChange={(event) => setRecipeId(event.target.value)}>
              <option value="">{copy.chooseRecipe}</option>
              {matchingRecipes.map((recipe) => (
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
          {!entry && attendanceSources.length > 0 && <div className="nf-attendance-template">
            <label className="field">
              <span>{locale==="pt-PT"?"Reutilizar presenças de outra refeição (opcional)":"Reuse attendance from another meal (optional)"}</span>
              <select value={attendanceSource} onChange={event=>setAttendanceSource(event.target.value)}>
                <option value="">{locale==="pt-PT"?"Escolher refeição anterior…":"Choose a previous meal…"}</option>
                {attendanceSources.map(source=><option key={source.entry.id} value={source.entry.id}>{formatDate(source.date,locale)} · {source.entry.recipe_name??mealLabel(target.mealType,locale)}</option>)}
              </select>
            </label>
            <button className="button secondary small" type="button" disabled={!attendanceSource}
              onClick={()=>{
                const source=attendanceSources.find(item=>item.entry.id===attendanceSource);
                if(!source)return;
                setParticipants(current=>copyAttendanceSelection(current,source.entry.participants.map(person=>person.person_id)));
                setAttendanceSource("");
              }}>{locale==="pt-PT"?"Usar apenas presenças":"Copy attendance only"}</button>
            <p className="muted">{locale==="pt-PT"?"Só copia quem está presente. As quantidades e unidades atuais mantêm-se; nada é guardado até confirmares.":"Copies attendees only. Current amounts and units are preserved; nothing is saved until confirmation."}</p>
          </div>}
          <div className="nf-presence-heading"><h3>{copy.participants}</h3><span role="status">{present.length}/{people.length} {locale==="pt-PT"?"presentes":"attending"}{unconfirmed.length>0 ? (locale==="pt-PT"?` · ${unconfirmed.length} por confirmar`:` · ${unconfirmed.length} unconfirmed`) : ""}</span><div className="button-row"><button type="button" className="button ghost small" onClick={()=>setParticipants(old=>old.map(person=>({...person,attendance:"present"})))}>{locale==="pt-PT"?"Selecionar todos":"Select all"}</button><button type="button" className="button ghost small" onClick={()=>setParticipants(old=>old.map(person=>({...person,attendance:"absent"})))}>{locale==="pt-PT"?"Selecionar nenhum":"Select none"}</button></div></div>
          {participants.map((participant) => {
            const person = people.find((candidate) => candidate.id === participant.personId);
            if (!person) return null;
            return (
              <div className="meal-plan-person" key={participant.personId}>
                <div className="meal-plan-person__check">
                  <PersonAvatar identity={person.id} familyIdentity={familyId} name={displayName(person)} appearance={person.avatar_appearance} size="sm" decorative/><strong>{displayName(person)}</strong>
                </div>
                <label className="field nf-attendance-decision">
                  <span>{locale==="pt-PT"?"Presença":"Attendance"}</span>
                  <select value={participant.attendance} onChange={event=>patchParticipant(participant.personId,{attendance:event.target.value as AttendanceDecision})}>
                    <option value="unconfirmed">{locale==="pt-PT"?"Por confirmar":"Unconfirmed"}</option>
                    <option value="present">{locale==="pt-PT"?"Presente":"Present"}</option>
                    <option value="absent">{locale==="pt-PT"?"Ausente":"Absent"}</option>
                  </select>
                </label>
                <label className="field">
                  <span>{copy.quantity} <small>({copy.defaultPortion})</small></span>
                  <input
                    disabled={participant.attendance!=="present"}
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
                    disabled={participant.attendance!=="present" || !participant.quantity.trim()}
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
        {unconfirmed.length>0&&<p role="status" className="nf-attendance-warning">{locale==="pt-PT"?`Faltam ${unconfirmed.length} confirmações de presença. Não serão tratadas como ausências.`:`${unconfirmed.length} attendance decisions remain unconfirmed. They will not be treated as absences.`}</p>}
        <section className="nf-meal-save-summary" aria-label={locale==="pt-PT"?"Resumo antes de guardar":"Summary before saving"}><span className="eyebrow">{locale==="pt-PT"?"VAI PARA O PLANO":"READY FOR THE PLANNER"}</span><h3>{selectedRecipe?.name??copy.chooseRecipe}</h3><p>{formatDate(target.date,locale)} · {mealLabel(target.mealType,locale)} · {localTime} · {location||"—"}</p><div className="nf-summary-people">{present.map(participant=><span key={participant.personId}>{displayName(people.find(person=>person.id===participant.personId)!)} · {participant.quantity?`${participant.quantity} ${participant.unit}`:copy.defaultPortion}</span>)}</div>{!present.length&&<p role="status">{copy.noPeople}</p>}</section>
        <div className="meal-plan-editor__actions">
          <button
            className="button primary"
            disabled={busy || !recipeId || !present.length || unconfirmed.length>0 || eligibleRecipes.length === 0}
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
      </fieldset></form>
    </section>
  );
}

export default function FamilyMealsScreen({
  familyId,
  referenceDate,
  initialDate,
  onDateChange,
  selectedMealType,
  onMealSelectionChange,
  mode,
  onModeChange,
  onDataChanged,
}: {
  familyId: string;
  referenceDate?: string;
  initialDate?: string;
  onDateChange?:(date:string)=>boolean;
  selectedMealType?: MealType;
  onMealSelectionChange?: (selection: {date: string; mealType: MealType} | null) => boolean | void;
  mode: FamilyMealsMode;
  onModeChange: (mode: FamilyMealsMode) => boolean|void;
  onDataChanged?: () => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [reviewLoadError,setReviewLoadError]=useState(false);
  const [reviewRecipes,setReviewRecipes]=useState<ReviewRecipe[]>([]);
  useEffect(()=>{let cancelled=false;setReviewLoadError(false);setReviewRecipes([]);void listRecipeReviews(familyId).then(r=>{if(!cancelled)setReviewRecipes(r);}).catch(()=>{if(!cancelled)setReviewLoadError(true);});return()=>{cancelled=true;};},[familyId]);
  const [plan, setPlan] = useState<FamilyMealPlan | null>(null);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [editing, setEditing] = useState<EditTarget | null>(null);
  const [heroSuggestion, setHeroSuggestion] = useState<HeroSuggestedMeal | null>(null);
  const requestEditorClose = useRef<() => void>(() => {});
  const [mealSelection,setMealSelection]=useState<{date:string;mealType:MealType}|null>(()=>initialDate&&selectedMealType?{date:initialDate,mealType:selectedMealType}:null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [browsingDate, setBrowsingDate] = useState(
    initialDate ?? referenceDate ?? localDateValue(),
  );

  useEffect(() => {
    setBrowsingDate(initialDate ?? referenceDate ?? localDateValue());
  }, [familyId, initialDate]);
  useEffect(() => {
    setEditing(null);
    setHeroSuggestion(null);
  }, [familyId]);
  useEffect(() => {
    setMealSelection(initialDate && selectedMealType ? {date:initialDate,mealType:selectedMealType} : null);
  }, [familyId, initialDate, selectedMealType]);

  // Keep the plan request identity stable when selecting another day or meal
  // inside the same week. Changing the URL must not unmount the weekly map.
  const scopeDate = mode === "week" ? startOfWeekDate(browsingDate) : browsingDate;
  const request = useMemo(() => {
    if (mode === "recommend" || mode === "prepare") return null;
    return {startDate: scopeDate, days: mode === "today" ? 1 : 7};
  }, [mode, scopeDate]);

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
          setError(mealPlanErrorText(caught, locale));
        }
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [familyId, request, revision]);

  function navigateDate(value:string|((current:string)=>string)){
    const next=typeof value==="function"?value(browsingDate):value;
    if(onDateChange?.(next)===false)return;setEditing(null);setBrowsingDate(next);
  }
  function refreshPlan() {
    setRevision((current) => current + 1);
    onDataChanged?.();
  }

  function closeEditor(changed = false) {
    setEditing(null);
    if (changed) refreshPlan();
  }

  const consumptionDate = browsingDate;

  if (mode === "prepare") return <Suspense fallback={<p role="status">{copy.loading}</p>}><PlanningJourney key={familyId} familyId={familyId} referenceDate={referenceDate ?? localDateValue()} onPlanChanged={onDataChanged} onOpenAgenda={week => {if(week)navigateDate(week);onModeChange("week");}} /></Suspense>;

  return (
    <div className="family-meals-screen">
      {mode !== "week" ? (
      <header className="screen-header compact-screen-header family-meals-header">
        <div>
          <span className="eyebrow">Plano</span>
          <h1>{copy.title}</h1>
          <p>{copy.help}</p>
        </div>
      </header>
      ) : null}
      {reviewLoadError && <p role="status">{locale==="pt-PT"?"Não foi possível carregar as alternativas dos ingredientes.":"Ingredient alternatives could not be loaded."}</p>}
      {mode === "week" && people.length > 0 ? (
        <NextMealHero
          familyId={familyId}
          timezone={plan?.timezone ?? people[0]?.timezone ?? "Europe/Lisbon"}
          people={people}
          revision={revision}
          onOpen={(date, mealType, entry) => {
            navigateDate(date);
            setHeroSuggestion(null);
            if (entry) {
              if (onMealSelectionChange?.({date,mealType}) === false) return;
              setMealSelection({date,mealType});
            } else {
              if (onMealSelectionChange?.(null) === false) return;
              setMealSelection(null);
              setEditing({date,mealType,entry:null});
            }
          }}
          onReview={(suggested) => {
            if (onMealSelectionChange?.({date:suggested.date,mealType:suggested.mealType}) === false) return;
            navigateDate(suggested.date);
            setEditing(null);
            setHeroSuggestion(suggested);
            setMealSelection({date:suggested.date,mealType:suggested.mealType});
          }}
        />
      ) : null}

      {mode !== "week" ? (
        <nav className="secondary-tabs family-meals-tabs" aria-label={copy.navigation}>
        <button type="button" onClick={() => onModeChange("prepare")}>{locale === "pt-PT" ? "Planear próxima semana" : "Plan next week"}</button>
        <button
          className={mode === "today" ? "active" : ""}
          onClick={() => {
            if(onModeChange("today")===false)return;setEditing(null);
          }}
          type="button"
        >
          {copy.today}
        </button>
        <button
          className=""
          onClick={() => {
            if(onModeChange("week")===false)return;setEditing(null);
          }}
          type="button"
        >
          {copy.week}
        </button>
        <button
          className={mode === "recommend" ? "active" : ""}
          onClick={() => {
            if(onModeChange("recommend")===false)return;setEditing(null);
          }}
          type="button"
        >
          {copy.recommend}
        </button>
      </nav>
      ) : null}

      {mode !== "recommend" ? (
        <nav className="family-meals-date-nav" aria-label={copy.dateNavigation}>
          <button
            className="button ghost"
            onClick={() => {
              navigateDate((current) => addPlanDays(current, mode === "today" ? -1 : -7));
            }}
            type="button"
          >
            {mode === "today" ? copy.previousDay : copy.previousWeek}
          </button>
          <button
            className="button secondary"
            onClick={() => {
              navigateDate(referenceDate ?? localDateValue());
            }}
            type="button"
          >
            {mode === "today" ? copy.backToToday : copy.backToThisWeek}
          </button>
          <button
            className="button ghost"
            onClick={() => {
              navigateDate((current) => addPlanDays(current, mode === "today" ? 1 : 7));
            }}
            type="button"
          >
            {mode === "today" ? copy.nextDay : copy.nextWeek}
          </button>
        </nav>
      ) : null}

      {mode === "recommend" ? <Suspense fallback={<div className="shell-loading" role="status">{copy.loading}</div>}><MealPlanner familyId={familyId} /></Suspense> : null}
      {mode !== "recommend" && error ? (
        <div className="error-banner" role="alert">
          <strong>{copy.error}</strong><span>{error}</span>
        </div>
      ) : null}
      {mode !== "recommend" && busy ? (
        <div className="shell-loading" role="status">{copy.loading}</div>
      ) : null}

      {mode !== "recommend" && !busy && plan ? (
        mode === "week" ? (
          <Suspense fallback={<div className="shell-loading" role="status">{copy.loading}</div>}><WeeklyProposalPreview
            simpleWeekView
            heroSuggestion={heroSuggestion}
            initialDate={initialDate ?? browsingDate}
            initialSelection={mealSelection} onSelectionChange={(selection)=>{
              if(onMealSelectionChange?.(selection)===false)return false;
              setMealSelection(selection);
              if (!selection || selection.date !== heroSuggestion?.date || selection.mealType !== heroSuggestion?.mealType) setHeroSuggestion(null);
              return true;
            }} onMealCommitted={onDataChanged}
            familyId={familyId}
            onEdit={(date, mealType, entry) => {
              // An editor replaces the detail drawer; it must never be stacked
              // behind it or leave a stale meal selection in the URL.
              if (onMealSelectionChange?.(null) === false) return;
              setMealSelection(null);
              setEditing({ date, mealType, entry });
            }}
            onPlanChanged={refreshPlan}
            people={people}
            plan={plan}
            weekStart={plan.start_date}
          /></Suspense>
        ) : (
          <div className="meal-plan-days today">
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
                          disabled={
                            slot.meals.length > 0 && slot.meals[0]?.status !== "planned"
                          }
                          onClick={() =>
                            setEditing({
                              date: day.date,
                              mealType: slot.meal_type,
                              entry: slot.meals[0] ?? null,
                            })
                          }
                          type="button"
                        >
                          {slot.meals.length === 0
                            ? `+ ${copy.add}`
                            : slot.meals[0]?.transformations.length
                              ? copy.view
                              : copy.edit}
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
                                  <SavedMealChanges entry={entry} recipes={reviewRecipes}/>
                                  {entry.transformations.map((transformation) => (
                                    <span
                                      className="meal-plan-entry__transformation"
                                      key={transformation.id}
                                    >
                                      <b>{transformationLabel(transformation.transformation_kind, locale)}</b>
                                      {" · "}
                                      {transformation.source_food_name} →{" "}
                                      {transformation.replacement_food_name}
                                    </span>
                                  ))}
                                </span>
                                <span className="meal-plan-entry__status">
                                  {statusLabel(entry.status, locale)}
                                  {entry.status === "planned"
                                    ? ` · ${entry.transformations.length ? copy.view : copy.edit}`
                                    : ` · ${copy.locked}`}
                                </span>
                              </button>
                              {entry.status !== "planned" ? (
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
      {editing ? (
        <ContextDrawer
          title={`${mealLabel(editing.mealType, locale)} · ${formatDate(editing.date, locale)}`}
          closeLabel={copy.cancel}
          onRequestClose={() => requestEditorClose.current()}
          wide
        >
          <MealEditForm
            key={`${familyId}:${editing.entry?.id ?? "new"}:${editing.date}:${editing.mealType}`}
            familyId={familyId}
            onDone={closeEditor}
            registerClose={(close) => { requestEditorClose.current = close; }}
            people={people}
            recipes={recipes}
            attendanceSources={(plan?.days ?? []).flatMap(day=>day.date>=editing.date?[]:day.slots
              .filter(slot=>slot.meal_type===editing.mealType)
              .flatMap(slot=>slot.meals.filter(entry=>entry.status==="planned"&&entry.participants.length>0)
                .map(entry=>({date:day.date,entry}))))}
            target={editing}
          />
        </ContextDrawer>
      ) : null}
    </div>
  );
}
