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
import { familyLocalDate, nextMealSlot } from "./nextMealHero";
import {
  recommendationCandidates,
} from "./recommendationPlanning";
import Icon from "./ui/Icon";
import "./next-meal-hero.css";

export type HeroSuggestedMeal = {
  date: string;
  mealType: MealType;
  request: SharedWeeklyPlanProposalRequest;
  proposal: SharedWeeklyPlanProposal;
};

type HeroImage = { src: string; author: string; source: string; license: string };

/** Deliberately curated, not keyword-based image matching.
 * A photo must not misrepresent the actual recipe or imply nutritional validation.
 * Wikimedia Commons CC0 1.0; retain source even for a public-domain image.
 */
export function verifiedRecipePhoto(name: string | null): HeroImage | null {
  const normalized = name?.normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim().toLowerCase() ?? "";
  const photos: Record<string, { file: string; author: string }> = {
    "salmao no forno com ervas": {file:"Steckenroth, salmon on baked vegetables.jpg", author:"Steckenroth"},
    "salmao no forno com ervinhas da provenca": {file:"Steckenroth, salmon on baked vegetables.jpg", author:"Steckenroth"},
    "pao, queijo e tomate": {file:"Toast with cheddar cheese and tomato.jpg", author:"OKJaguar"},
    "torrada com queijo": {file:"Toast with cheddar cheese and tomato.jpg", author:"OKJaguar"},
    "frango rapido": {file:"Chicken plate.jpg", author:"Wikimedia Commons contributor"},
    "omelete de espinafres": {file:"An omelette.jpg", author:"Wikimedia Commons contributor"},
  };
  const entry = photos[normalized];
  if (!entry) return null;
  const encoded = encodeURIComponent(entry.file).replace(/%2F/g, "/");
  return {
    src: `https://commons.wikimedia.org/wiki/Special:FilePath/${encoded}?width=900`,
    author: entry.author,
    source: `https://commons.wikimedia.org/wiki/File:${entry.file.replace(/ /g, "_")}`,
    license: "CC0 1.0",
  };
}

type LoadState = { slot: string; proposal: SharedWeeklyPlanProposal; request: SharedWeeklyPlanProposalRequest } | null;
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
    const first = people[0];
    const rejectedKeys = new Set(rejected);
    // Bootstrap and proposal are read-only; there is no automatic meal save.
    void (async () => {
      const bootstrap = await getRecommendationBootstrap(first.id, slot.scheduledAt, {ensureState:false});
      const candidates = recommendationCandidates(
        bootstrap.candidates.filter(candidate => !rejectedKeys.has(candidate.catalog_key)), ["cooked"], slot.mealType,
      );
      if (!candidates.length) return null;
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
      return {request, proposal: await requestSharedWeeklyPlanProposal(familyId, request)};
    })().then(result => {
      if (!cancelled && result) setSuggestion({slot: identity, ...result});
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
  const photo = verifiedRecipePhoto(name);
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
  const secondary = ready ? copy.planned : choice ? copy.disclaimer :
    busy ? copy.emptyHelp : people.length < 2 ? copy.emptyHelp : copy.noSuggestionHelp;

  return (
    <section className="nf-next-meal-hero" aria-label={copy.title}>
      <div className="nf-next-meal-hero__art">
        {photo ? <img src={photo.src} alt="" loading="lazy" referrerPolicy="no-referrer" /> :
          <img src="/images/shared-meal.svg" alt="" aria-hidden="true" />}
      </div>
      <div className="nf-next-meal-hero__info">
        <span className="nf-next-meal-hero__eyebrow">{status}</span>
        <h2>{heading}</h2>
        <p>{secondary}</p>
        <div className="nf-next-meal-hero__context"><Icon name="clock"/>{timeLabel} · {mealLabel}</div>
        {photo ? <a className="nf-next-meal-hero__credit" href={photo.source} target="_blank" rel="noopener noreferrer">
          {copy.photo}: {photo.author} · {photo.license}
        </a> : <small className="nf-next-meal-hero__credit">{copy.illustration}</small>}
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
