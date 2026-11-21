import { useEffect, useMemo, useState } from "react";
import { getFamilyMealPlan } from "./api/client";
import type { FamilyMealPlan, MealPlanEntry, MealType } from "./api/mealPlanTypes";
import { getRecommendationBootstrap } from "./api/recommendationClient";
import { requestSharedWeeklyPlanProposal } from "./api/weeklyPlanningClient";
import type {
  SharedWeeklyPlanProposal, SharedWeeklyPlanProposalRequest,
} from "./api/weeklyPlanningTypes";
import type { Person } from "./api/types";
import { useI18n } from "./i18n";
import { familyLocalDate, nextMealSlot, mealProposalUnavailableReason } from "./nextMealSelection";
import {
  recommendationCandidates,
} from "./recommendationPlanning";
import Icon from "./ui/Icon";
import { resolveMealHeroImage } from "./mealHeroImages";

export type HeroSuggestedMeal = {
  date: string;
  mealType: MealType;
  request: SharedWeeklyPlanProposalRequest;
  proposal: SharedWeeklyPlanProposal;
};

type LoadState = { slot: string; proposal: SharedWeeklyPlanProposal; request: SharedWeeklyPlanProposalRequest; candidateCount: number } | null;
const LABELS = {
  "pt-PT": { title: "PRÓXIMA REFEIÇÃO", planned: "Planeada para a família", proposed: "PROPOSTA NUTRIFLOW",
    review: "Rever e adaptar", open: "Ver refeição", retry: "Outra sugestão",
    pending: "A calcular uma sugestão…", noSuggestion: "Nenhuma proposta elegível confirmada",
    noSuggestionHelp: "Revê presenças, preferências e regras obrigatórias no planeamento. Não foi inventada uma receita.",
    needPeople: "A recomendação familiar automática exige pelo menos duas pessoas. Revê o plano para escolher a refeição.",
    empty: "Próxima refeição por definir", emptyHelp: "O planeamento e as restrições de cada pessoa orientam a escolha.",
    disclaimer: "Proposta por confirmar · a elegibilidade depende dos dados disponíveis.",
    illustration: "Imagem ilustrativa; não corresponde necessariamente à receita.",
    photo: "Fotografia ilustrativa", unavailable: "Não foi possível calcular a proposta. O plano continua intacto.",
    schedule: "Planeamento",
  },
  en: { title: "NEXT MEAL", planned: "Planned family meal", proposed: "NUTRIFLOW PROPOSAL",
    review: "Review and adapt", open: "View meal", retry: "Another suggestion",
    pending: "Calculating a suggestion…", noSuggestion: "No confirmed eligible proposal",
    noSuggestionHelp: "Review attendance, preferences and mandatory rules in planning. No recipe has been invented.",
    needPeople: "Automatic family recommendation requires at least two people. Review your meal plan.",
    empty: "Next meal not decided", emptyHelp: "Planning and each person's restrictions guide the choice.",
    disclaimer: "Unconfirmed proposal · eligibility depends on the available evidence.",
    illustration: "Illustrative image; may not represent the recipe.",
    photo: "Illustrative photograph", unavailable: "The proposal could not be calculated. Your plan remains unchanged.",
    schedule: "Planner",
  },
} as const;

export default function NextMealHero({
  familyId, timezone, people, revision, onOpen, onReview,
}: {
  familyId: string;
  timezone: string;
  people: Person[];
  revision: number;
  onOpen: (date: string, mealType: MealType, entry: MealPlanEntry | null) => void;
  onReview: (value: HeroSuggestedMeal) => void;
}) {
  const { locale } = useI18n();
  const copy = LABELS[locale];
  const [now, setNow] = useState(() => Date.now());
  const today = familyLocalDate(now, timezone);
  const [plan, setPlan] = useState<FamilyMealPlan | null>(null);
  const [planScope, setPlanScope] = useState("");
  const [loadError, setLoadError] = useState(false);
  const [suggestion, setSuggestion] = useState<LoadState>(null);
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const [failedKey, setFailedKey] = useState<string | null>(null);
  const [emptyCatalogKey, setEmptyCatalogKey] = useState<string | null>(null);
  const [rejected, setRejected] = useState<string[]>([]);

  useEffect(() => {
    const interval = window.setInterval(() => setNow(Date.now()), 30_000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setPlanScope("");
    setPlan(null);
    setLoadError(false);
    void getFamilyMealPlan(familyId, today, 2).then(result => {
      if (!cancelled) { setPlan(result); setPlanScope(`${familyId}:${today}:${revision}`); }
    }).catch(() => { if (!cancelled) setLoadError(true); });
    return () => { cancelled = true; };
  }, [familyId, today, revision]);

  const currentScope = `${familyId}:${today}:${revision}`;
  const slot = useMemo(() => plan && planScope === currentScope ? nextMealSlot(plan, now) : null,
    [plan, planScope, currentScope, now]);
  const slotId = slot ? `${familyId}:${slot.date}:${slot.mealType}` : null;
  const rejectedKey = rejected.join("|");
  const peopleKey = people.map(person => person.id).join("|");

  useEffect(() => {
    setRejected([]);
  }, [slotId, peopleKey]);

  useEffect(() => {
    if (!slot || slot.entry || people.length < 2 || !slotId) return;
    let cancelled = false;
    const identity = `${slotId}:${rejectedKey}`;
    setSuggestion(null);
    setPendingKey(identity);
    setFailedKey(null);
    setEmptyCatalogKey(null);
    const first = people[0];
    if (!first) return;
    const rejectedKeys = new Set(rejected);
    // Bootstrap and proposal are read-only; there is no automatic meal save.
    void (async () => {
      const bootstrap = await getRecommendationBootstrap(first.id, slot.scheduledAt, {ensureState:false});
      const candidates = recommendationCandidates(
        bootstrap.candidates.filter(candidate => !rejectedKeys.has(candidate.catalog_key)), ["cooked"], slot.mealType,
      );
      if (!candidates.length) return {empty: true as const};
      const request: SharedWeeklyPlanProposalRequest = {
        person_ids: people.map(person => person.id),
        slots: [{
          slot_key: `${slot.date}:${slot.mealType}`,
          person_ids: people.map(person => person.id),
          planning_date: slot.date,
          scheduled_at: slot.scheduledAt,
          meal_type: slot.mealType,
          candidates,
          location: "Casa",
          available_minutes: null,
          has_kitchen: true,
          source_kinds: ["home", "pantry"],
          delivery_provider_keys: [],
          provisional_history: [],
          auto_size_portions: true,
        }],
        max_combinations: 128,
      };
      return {request, proposal: await requestSharedWeeklyPlanProposal(familyId, request), candidateCount:candidates.length};
    })().then(result => {
      if (!cancelled && result) {
        if ("empty" in result) setEmptyCatalogKey(identity);
        else setSuggestion({slot: identity, ...result});
      }
    }).catch(() => {
      if (!cancelled) setFailedKey(identity);
    }).finally(() => {
      if (!cancelled) setPendingKey(null);
    });
    return () => { cancelled = true; };
  }, [familyId, slotId, slot?.scheduledAt, slot?.entry, rejectedKey, peopleKey]);

  const identity = slotId ? `${slotId}:${rejectedKey}` : null;
  const currentSuggestion = suggestion?.slot === identity ? suggestion : null;
  const choice = currentSuggestion?.proposal.selected_plan?.choices[0] ?? null;
  const name = slot?.entry?.recipe_name ?? slot?.entry?.title ?? choice?.candidate_name ?? null;
  const replacement = choice?.transformation?.operation;
  const replacementLabel = replacement ? `${replacement.source_food_name} → ${replacement.replacement_food_name}` : null;
  const noProposalDetails = slot && !slot.entry && !choice && (emptyCatalogKey===identity || currentSuggestion)
    ? mealProposalUnavailableReason(slot.mealType, emptyCatalogKey===identity ? 0 : currentSuggestion?.candidateCount ?? null,
      currentSuggestion?.proposal.skipped_slots.flatMap(item=>item.exclusion_reasons) ?? [],locale)
    : null;
  const photo = resolveMealHeroImage({planned:slot?.entry, proposal:slot?.entry ? null : choice});
  const [failedPhoto, setFailedPhoto] = useState<string | null>(null);
  const showingPhoto = photo && photo.src !== failedPhoto ? photo : null;
  const timeLabel = slot ? new Intl.DateTimeFormat(locale, {
    weekday:"short", day:"numeric", month:"short", hour:"2-digit", minute:"2-digit", timeZone: timezone,
  }).format(new Date(slot.scheduledAt)) : "";
  const mealLabel = slot ? ({
    "pt-PT": {breakfast:"Pequeno-almoço",lunch:"Almoço",snack:"Lanche",dinner:"Jantar"},
    en: {breakfast:"Breakfast",lunch:"Lunch",snack:"Snack",dinner:"Dinner"},
  }[locale][slot.mealType]) : "";
  const ready = Boolean(slot && slot.entry);
  const busy = pendingKey === identity;
  const status = ready ? copy.planned : choice ? copy.proposed : copy.title;
  const heading = name ?? (busy ? copy.pending : failedKey === identity || loadError ? copy.unavailable :
    people.length < 2 ? copy.needPeople : copy.noSuggestion);
  const secondary = ready ? copy.planned : choice ? (replacementLabel ? `${locale==="pt-PT"?"Adaptação proposta — ingrediente a trocar":"Proposed adaptation — ingredient to replace"}: ${replacementLabel}. ${copy.disclaimer}` : copy.disclaimer) :
    busy ? copy.emptyHelp : people.length < 2 ? copy.emptyHelp : noProposalDetails ?? copy.noSuggestionHelp;

  return (
    <section className="nf-next-meal-hero" aria-label={copy.title}>
      <div className="nf-next-meal-hero__art">
        {showingPhoto ? <img key={showingPhoto.src} src={showingPhoto.src} alt={showingPhoto.alt}
          loading="eager" referrerPolicy="no-referrer" onError={() => setFailedPhoto(showingPhoto.src)} /> :
          <img src="/images/shared-meal.svg" alt="" aria-hidden="true" />}
      </div>
      <div className="nf-next-meal-hero__info">
        <span className="nf-next-meal-hero__eyebrow">{status}</span>
        <h2>{heading}</h2>
        <p>{secondary}</p>
        <div className="nf-next-meal-hero__context"><Icon name="clock"/>{timeLabel} · {mealLabel}</div>
        {showingPhoto ? (showingPhoto.source ?
          <a className="nf-next-meal-hero__credit" href={showingPhoto.source} target="_blank" rel="noopener noreferrer">
            {copy.photo}: {showingPhoto.author} · {showingPhoto.license}
          </a> :
          <small className="nf-next-meal-hero__credit">{copy.photo}</small>
        ) : <small className="nf-next-meal-hero__credit">{copy.illustration}</small>}
      </div>
      <div className="nf-next-meal-hero__actions">
        {slot && <button className="button primary" type="button" onClick={() => {
          if (choice && currentSuggestion) {
            onReview({date:slot.date,mealType:slot.mealType,request:currentSuggestion.request,proposal:currentSuggestion.proposal});
          } else onOpen(slot.date,slot.mealType,slot.entry);
        }}>
          <Icon name={ready ? "book" : choice ? "spark" : "calendar"}/>
          {ready ? copy.open : choice ? copy.review : copy.schedule}
        </button>}
        {slot && choice && <button className="button ghost small" type="button" onClick={() => {
          setRejected(previous => [...previous,choice.candidate_key]);
        }}>{copy.retry}</button>}
      </div>
    </section>
  );
}
