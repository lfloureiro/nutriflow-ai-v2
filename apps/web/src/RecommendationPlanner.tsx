import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  ApiError,
  listFamilyPersons,
  requestPracticalRecommendation,
  submitRecommendationDecision,
} from "./api/client";
import { syncMealDeliveryProvider } from "./api/mealDeliveryClient";
import type { MealDeliverySync } from "./api/mealDeliveryTypes";
import { getRecommendationBootstrap } from "./api/recommendationClient";
import { syncRestaurantMenus } from "./api/restaurantDiscoveryClient";
import type { RestaurantMenuSync } from "./api/restaurantDiscoveryTypes";
import {
  planSharedPracticalRecommendation,
  requestSharedPracticalRecommendation,
} from "./api/sharedRecommendationClient";
import type {
  SharedPracticalPlan,
  SharedPracticalRecommendation,
  SharedPracticalRecommendationRequest,
  SharedRecommendationOption,
} from "./api/sharedRecommendationTypes";
import { getPersonMealDiscovery } from "./api/setupClient";
import type { PersonMealDiscovery } from "./api/setupTypes";
import type {
  CommercialOffer,
  HumanPortionGuidance,
  Person,
  PracticalRecommendationRequest,
  PracticalRecommendationRun,
  RecommendationDecision,
  RecommendationHistoryHint,
  RecommendationOption,
} from "./api/types";
import { useI18n, type Locale } from "./i18n";
import { localDateValue, scheduledIso } from "./planning";
import RecommendationNutritionBudgetPanel from "./RecommendationNutritionBudget";
import {
  recommendationNutritionBudget,
  type RecommendationNutritionBudget,
} from "./recommendationNutrition";
import {
  DEFAULT_MEAL_TIMES,
  RECOMMENDATION_MEAL_TYPES,
  RECOMMENDATION_SOURCES,
  recommendationCandidates,
  recommendationDates,
  recommendationDeliveryProviderKeys,
  recommendationScheduledLocal,
  recommendationSourceKinds,
  type RecommendationMealType,
  type RecommendationPeriodMode,
  type RecommendationSource,
} from "./recommendationPlanning";

const MAX_VISIBLE_RESULTS = 3;
const RESTAURANT_LIMIT = 8;
const MAIN_MEAL_TYPES = new Set<RecommendationMealType>(["lunch", "dinner"]);

const COPY = {
  "pt-PT": {
    title: "Recomendar refeições",
    help: "Escolhe quem vai comer, quando e onde procurar. As receitas e os pratos disponíveis nas fontes selecionadas são avaliados em conjunto.",
    people: "Pessoas",
    peopleLower: "pessoas",
    allPeople: "Todos",
    period: "Período",
    single: "1 dia",
    range: "Vários dias",
    date: "Dia",
    startDate: "De",
    endDate: "Até",
    mealType: "Tipo de refeição",
    sources: "Onde procurar",
    cooked: "Receitas",
    cookedHelp: "Receitas partilhadas e da família, avaliadas pelas quantidades reais dos ingredientes",
    uber_eats: "Uber Eats",
    uber_eatsHelp: "Pratos disponíveis na Uber Eats, atualizados antes de calcular as recomendações",
    glovo: "Glovo",
    glovoHelp: "Pratos sincronizados quando existir acesso autorizado ao catálogo",
    bolt_food: "Bolt Food",
    bolt_foodHelp: "Pratos sincronizados quando existir acesso autorizado ao catálogo",
    restaurant: "Restaurantes",
    restaurantHelp: "Google Places/OSM → site oficial → ementa → prato com nutrição utilizável",
    sourceUnavailable: "Não está disponível para esta refeição ou para todas as pessoas selecionadas",
    more: "Mais opções",
    time: "Hora",
    location: "Área / local (override opcional)",
    minutes: "Tempo disponível (min)",
    recommend: "Obter recomendações",
    recommending: "A atualizar fontes e calcular recomendações…",
    noPeople: "Não existem pessoas nesta família.",
    peopleRequired: "Escolhe pelo menos uma pessoa.",
    sourceRequired: "Escolhe pelo menos uma origem disponível.",
    noCandidates: "Não existem receitas ou pratos com dados suficientes para esta refeição.",
    noResults: "Não foram encontradas refeições adequadas para este dia.",
    stateUnavailable: "Não foi possível preparar o orçamento nutricional para",
    error: "Não foi possível obter a recomendação",
    results: "Recomendações",
    best: "Melhor escolha",
    alternative: "Alternativa",
    planned: "Adicionada ao plano",
    accept: "Adicionar ao plano",
    reject: "Rejeitar",
    breakfast: "Pequeno-almoço",
    lunch: "Almoço",
    snack: "Lanche",
    dinner: "Jantar",
    from: "Onde obter",
    deliverySource: "Entrega",
    restaurantSource: "Restaurante",
    groupFit: "Adequação do grupo",
    suggestedAmounts: "Quantidades sugeridas",
    uberUpdated: "Uber Eats atualizada",
    uberDishes: "pratos observados",
    uberNutritionReady: "com nutrição utilizável",
    uberUnavailable: "Não foi possível atualizar a Uber Eats. Dados ainda válidos já guardados continuam a poder ser usados.",
    restaurantsUpdated: "Ementas atualizadas",
    restaurantsAnalysed: "restaurantes",
    menuDishes: "pratos encontrados",
    nutritionReady: "com nutrição utilizável",
    restaurantAreaRequired: "Configura uma área de restaurantes em Casa → Fontes ou indica uma área em Mais opções.",
    restaurantAreaMismatch: "As pessoas selecionadas têm áreas de restaurantes diferentes. Indica uma área comum em Mais opções.",
    restaurantUnavailable: "Não foi possível atualizar as ementas. As restantes fontes continuam disponíveis.",
    restaurantOnlyUnavailable: "Não foi possível atualizar as ementas e não foi selecionada outra fonte utilizável.",
    sourceGoogle: "Google Places",
    sourceOsm: "OpenStreetMap",
    dose: "dose",
    doses: "doses",
  },
  en: {
    title: "Meal recommendations",
    help: "Choose who will eat, when and where to search. Recipes and dishes from the selected sources are evaluated together.",
    people: "People",
    peopleLower: "people",
    allPeople: "Everyone",
    period: "Period",
    single: "1 day",
    range: "Several days",
    date: "Day",
    startDate: "From",
    endDate: "To",
    mealType: "Meal type",
    sources: "Where to search",
    cooked: "Recipes",
    cookedHelp: "Shared and Family recipes evaluated from real ingredient quantities",
    uber_eats: "Uber Eats",
    uber_eatsHelp: "Available Uber Eats dishes refreshed before recommendations are calculated",
    glovo: "Glovo",
    glovoHelp: "Synchronized dishes when authorized catalogue access is available",
    bolt_food: "Bolt Food",
    bolt_foodHelp: "Synchronized dishes when authorized catalogue access is available",
    restaurant: "Restaurants",
    restaurantHelp: "Google Places/OSM → official website → menu → nutritionally usable dish",
    sourceUnavailable: "Not available for this meal or every selected person",
    more: "More options",
    time: "Time",
    location: "Area / location (optional override)",
    minutes: "Available time (min)",
    recommend: "Get recommendations",
    recommending: "Refreshing sources and calculating recommendations…",
    noPeople: "There are no people in this Family.",
    peopleRequired: "Choose at least one person.",
    sourceRequired: "Choose at least one available source.",
    noCandidates: "There are no recipes or dishes with enough data for this meal.",
    noResults: "No suitable meals were found for this day.",
    stateUnavailable: "Could not prepare the nutrition budget for",
    error: "The recommendation could not be created",
    results: "Recommendations",
    best: "Best choice",
    alternative: "Alternative",
    planned: "Added to plan",
    accept: "Add to plan",
    reject: "Reject",
    breakfast: "Breakfast",
    lunch: "Lunch",
    snack: "Snack",
    dinner: "Dinner",
    from: "Where to get it",
    deliverySource: "Delivery",
    restaurantSource: "Restaurant",
    groupFit: "Group fit",
    suggestedAmounts: "Suggested amounts",
    uberUpdated: "Uber Eats refreshed",
    uberDishes: "dishes observed",
    uberNutritionReady: "with usable nutrition",
    uberUnavailable: "Uber Eats could not be refreshed. Previously stored data that is still valid can still be used.",
    restaurantsUpdated: "Menus refreshed",
    restaurantsAnalysed: "restaurants",
    menuDishes: "dishes found",
    nutritionReady: "with usable nutrition",
    restaurantAreaRequired: "Configure a restaurant area under Home base → Sources or enter an area in More options.",
    restaurantAreaMismatch: "The selected people have different restaurant areas. Enter one common area in More options.",
    restaurantUnavailable: "Menus could not be refreshed. Other selected sources remain available.",
    restaurantOnlyUnavailable: "Menus could not be refreshed and no other usable source was selected.",
    sourceGoogle: "Google Places",
    sourceOsm: "OpenStreetMap",
    dose: "serving",
    doses: "servings",
  },
} as const;

type DayResultBase = {
  date: string;
  scheduledLocal: string;
  personIds: string[];
  sources: RecommendationSource[];
  nutritionBudgets: RecommendationNutritionBudget[];
  error: string | null;
};

type SingleDayResult = DayResultBase & {
  mode: "single";
  run: PracticalRecommendationRun | null;
  request: PracticalRecommendationRequest | null;
};

type SharedDayResult = DayResultBase & {
  mode: "shared";
  run: SharedPracticalRecommendation | null;
  request: SharedPracticalRecommendationRequest | null;
};

type DayResult = SingleDayResult | SharedDayResult;

type BusyState =
  | { kind: "recommend" }
  | { kind: "single-decision"; optionId: string }
  | { kind: "shared-plan"; key: string }
  | null;

type OfferLike = Pick<
  CommercialOffer,
  | "candidate_key"
  | "source_kind"
  | "offer_key"
  | "provider_key"
  | "provider_name"
  | "location"
  | "total_known_price"
  | "currency"
>;

function errorText(error: unknown): string {
  if (error instanceof ApiError) return `${error.message} (HTTP ${error.status})`;
  return error instanceof Error ? error.message : String(error);
}

function displayName(person: Person): string {
  return [person.first_name, person.last_name].filter(Boolean).join(" ");
}

function formatDate(value: string, locale: Locale): string {
  return new Intl.DateTimeFormat(locale, {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function formatNumber(value: string, locale: Locale, maximumFractionDigits = 1): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return value;
  return new Intl.NumberFormat(locale, { maximumFractionDigits }).format(numeric);
}

function formatMoney(value: string, currency: string, locale: Locale): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return `${value} ${currency}`;
  try {
    return new Intl.NumberFormat(locale, { style: "currency", currency }).format(numeric);
  } catch {
    return `${formatNumber(value, locale, 2)} ${currency}`;
  }
}

function discoveryToRecommendationSources(
  discovery: PersonMealDiscovery,
): RecommendationSource[] {
  const mapped: RecommendationSource[] = [];
  if (discovery.meal_discovery_sources.includes("shared_recipes")) mapped.push("cooked");
  if (discovery.meal_discovery_sources.includes("uber_eats")) mapped.push("uber_eats");
  if (discovery.meal_discovery_sources.includes("glovo")) mapped.push("glovo");
  if (discovery.meal_discovery_sources.includes("bolt_food")) mapped.push("bolt_food");
  if (discovery.meal_discovery_sources.includes("restaurants")) mapped.push("restaurant");
  return mapped;
}

function commonRecommendationSources(
  personIds: string[],
  discoveryByPersonId: Record<string, PersonMealDiscovery>,
): RecommendationSource[] {
  if (personIds.length === 0) return [];
  const configured = personIds.map((personId) =>
    new Set(discoveryToRecommendationSources(discoveryByPersonId[personId]!)),
  );
  if (configured.some((set) => set.size === 0)) return [];
  return RECOMMENDATION_SOURCES.filter((source) =>
    configured.every((set) => set.has(source)),
  );
}

function sourceSupportsMeal(
  source: RecommendationSource,
  mealType: RecommendationMealType,
): boolean {
  if (source !== "cooked") return MAIN_MEAL_TYPES.has(mealType);
  return true;
}

export function restaurantAreaForPeople(
  personIds: string[],
  discoveryByPersonId: Record<string, PersonMealDiscovery>,
  override: string,
): string | null | "mismatch" {
  const normalizedOverride = override.trim();
  if (normalizedOverride) return normalizedOverride;
  const areas = new Set(
    personIds
      .map((personId) => discoveryByPersonId[personId]?.restaurant_area?.trim() ?? "")
      .filter(Boolean),
  );
  if (areas.size === 0) return null;
  if (areas.size > 1) return "mismatch";
  return [...areas][0] ?? null;
}

function matchingOffers(
  offers: OfferLike[],
  candidateKey: string,
  sources: RecommendationSource[],
): OfferLike[] {
  return offers.filter((offer) => {
    if (offer.candidate_key !== candidateKey) return false;
    if (offer.source_kind === "restaurant") return sources.includes("restaurant");
    if (offer.source_kind !== "delivery") return false;
    if (offer.provider_key === "uber_eats") return sources.includes("uber_eats");
    if (offer.provider_key === "glovo") return sources.includes("glovo");
    if (offer.provider_key === "bolt_food") return sources.includes("bolt_food");
    return false;
  });
}

function visibleSingleOptions(
  run: PracticalRecommendationRun,
  sources: RecommendationSource[],
): RecommendationOption[] {
  return run.options.filter((option) => {
    if (!option.eligible) return false;
    if (option.candidate_kind === "recipe") return sources.includes("cooked");
    return matchingOffers(run.commercial_offers, option.candidate_key, sources).length > 0;
  });
}

function visibleSharedOptions(
  run: SharedPracticalRecommendation,
  sources: RecommendationSource[],
): SharedRecommendationOption[] {
  return run.options.filter((option) => {
    if (!option.eligible) return false;
    if (option.candidate_kind === "recipe") return sources.includes("cooked");
    return matchingOffers(run.commercial_offers, option.candidate_key, sources).length > 0;
  });
}

function topCandidateKey(day: DayResult): string | null {
  if (!day.run) return null;
  const options =
    day.mode === "single"
      ? visibleSingleOptions(day.run, day.sources)
      : visibleSharedOptions(day.run, day.sources);
  return options.at(0)?.candidate_key ?? null;
}

function humanUnit(unit: string, quantity: string | null, locale: Locale): string {
  const normalized = unit.trim().toLocaleLowerCase();
  if (["serving", "portion", "dose"].includes(normalized)) {
    const numeric = quantity === null ? 1 : Number(quantity);
    return numeric === 1 ? COPY[locale].dose : COPY[locale].doses;
  }
  if (["qb", "q.b.", "q.b", "quanto baste"].includes(normalized)) return "q.b.";
  return unit;
}

function PortionGuidance({
  guidance,
  fallbackQuantity,
  fallbackUnit,
}: {
  guidance: HumanPortionGuidance | null;
  fallbackQuantity: string;
  fallbackUnit: string;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  if (!guidance || guidance.components.length === 0) {
    return (
      <p className="muted compact">
        {formatNumber(fallbackQuantity, locale)} {humanUnit(fallbackUnit, fallbackQuantity, locale)}
      </p>
    );
  }

  if (guidance.kind === "single_item") {
    const component = guidance.components[0]!;
    return (
      <p className="muted compact">
        {component.quantity === null ? "" : `${formatNumber(component.quantity, locale)} `}
        {humanUnit(component.unit, component.quantity, locale)}
      </p>
    );
  }

  return (
    <details className="portion-guidance">
      <summary>{copy.suggestedAmounts}</summary>
      <ul className="compact-list">
        {guidance.components.map((component, index) => (
          <li key={`${component.name}:${component.unit}:${index}`}>
            <strong>{component.name}</strong>{" "}
            {component.qualitative || component.quantity === null
              ? humanUnit(component.unit, null, locale)
              : `${formatNumber(component.quantity, locale, 2)} ${humanUnit(component.unit, component.quantity, locale)}`}
          </li>
        ))}
      </ul>
    </details>
  );
}

function SourceChoice({
  source,
  selected,
  disabled,
  onChange,
}: {
  source: RecommendationSource;
  selected: boolean;
  disabled: boolean;
  onChange: () => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const helpKey = `${source}Help` as
    | "cookedHelp"
    | "uber_eatsHelp"
    | "glovoHelp"
    | "bolt_foodHelp"
    | "restaurantHelp";
  return (
    <label className={`recommend-source-card ${selected ? "selected" : ""} ${disabled ? "disabled" : ""}`}>
      <input checked={selected} disabled={disabled} onChange={onChange} type="checkbox" />
      <span>
        <strong>{copy[source]}</strong>
        <small>{disabled ? copy.sourceUnavailable : copy[helpKey]}</small>
      </span>
    </label>
  );
}

function OfferList({ offers }: { offers: OfferLike[] }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  if (offers.length === 0) return null;
  return (
    <div className="detail-block">
      <span className="detail-label">{copy.from}</span>
      <div className="offer-list">
        {offers.map((offer) => (
          <div className="offer-row" key={offer.offer_key}>
            <div>
              <strong>{offer.provider_name ?? offer.provider_key}</strong>
              <span className="muted">
                {offer.source_kind === "restaurant" ? copy.restaurantSource : copy.deliverySource}
                {offer.location ? ` · ${offer.location}` : ""}
              </span>
            </div>
            <strong>{formatMoney(offer.total_known_price, offer.currency, locale)}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function ResultEyebrow({ rank }: { rank: number | null }) {
  const { locale } = useI18n();
  return <span className="eyebrow">{rank === 1 ? COPY[locale].best : COPY[locale].alternative}</span>;
}

function SingleResultCard({
  option,
  run,
  sources,
  decision,
  busy,
  onDecision,
}: {
  option: RecommendationOption;
  run: PracticalRecommendationRun;
  sources: RecommendationSource[];
  decision: RecommendationDecision | undefined;
  busy: boolean;
  onDecision: (option: RecommendationOption, action: "accepted" | "rejected") => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const offers = matchingOffers(run.commercial_offers, option.candidate_key, sources);
  return (
    <article className={`recommendation-card eligible ${option.rank === 1 ? "best" : ""}`}>
      <div className="recommendation-card__header">
        <div>
          <ResultEyebrow rank={option.rank} />
          <h3>{option.candidate_name}</h3>
          <PortionGuidance
            fallbackQuantity={option.quantity}
            fallbackUnit={option.quantity_unit}
            guidance={option.portion_guidance}
          />
        </div>
        {option.nutrition.energy_kcal !== null ? (
          <div className="energy-pill">
            <strong>{formatNumber(option.nutrition.energy_kcal, locale, 0)}</strong>
            <span>kcal</span>
          </div>
        ) : null}
      </div>
      <OfferList offers={offers} />
      {option.explanation.length > 0 ? (
        <div className="detail-block">
          <ul className="compact-list">
            {option.explanation.slice(0, 4).map((message) => <li key={message}>{message}</li>)}
          </ul>
        </div>
      ) : null}
      {decision ? (
        <div className="decision-result" role="status">
          <strong>{decision.action === "accepted" ? copy.planned : copy.reject}</strong>
        </div>
      ) : (
        <div className="button-row">
          <button
            className="button primary"
            disabled={busy}
            onClick={() => onDecision(option, "accepted")}
            type="button"
          >
            {copy.accept}
          </button>
          <button
            className="button ghost"
            disabled={busy}
            onClick={() => onDecision(option, "rejected")}
            type="button"
          >
            {copy.reject}
          </button>
        </div>
      )}
    </article>
  );
}

function SharedResultCard({
  option,
  run,
  sources,
  peopleById,
  planned,
  busy,
  onPlan,
}: {
  option: SharedRecommendationOption;
  run: SharedPracticalRecommendation;
  sources: RecommendationSource[];
  peopleById: Map<string, Person>;
  planned: SharedPracticalPlan | undefined;
  busy: boolean;
  onPlan: (option: SharedRecommendationOption) => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const offers = matchingOffers(run.commercial_offers, option.candidate_key, sources);
  return (
    <article className={`recommendation-card eligible shared-recommendation-card ${option.rank === 1 ? "best" : ""}`}>
      <div className="recommendation-card__header">
        <div>
          <ResultEyebrow rank={option.rank} />
          <h3>{option.candidate_name}</h3>
          <p className="muted compact">
            {option.participants.length} {copy.peopleLower}
            {option.average_score !== null
              ? ` · ${copy.groupFit}: ${formatNumber(option.average_score, locale, 2)}`
              : ""}
          </p>
        </div>
      </div>
      <div className="shared-participant-list">
        {option.participants.map((participant) => {
          const person = peopleById.get(participant.person_id);
          return (
            <div className="shared-participant-row" key={participant.person_id}>
              <div>
                <strong>{person ? displayName(person) : participant.person_id}</strong>
                <PortionGuidance
                  fallbackQuantity={participant.quantity}
                  fallbackUnit={participant.quantity_unit}
                  guidance={participant.portion_guidance}
                />
              </div>
              {participant.energy_kcal !== null ? (
                <span>{formatNumber(participant.energy_kcal, locale, 0)} kcal</span>
              ) : null}
            </div>
          );
        })}
      </div>
      <OfferList offers={offers} />
      {planned ? (
        <div className="decision-result" role="status"><strong>{copy.planned}</strong></div>
      ) : (
        <div className="button-row">
          <button className="button primary" disabled={busy} onClick={() => onPlan(option)} type="button">
            {copy.accept}
          </button>
        </div>
      )}
    </article>
  );
}

function DeliverySyncSummary({ result }: { result: MealDeliverySync }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const nutritionReady = result.items.filter((item) => item.eligible_for_nutrition_ranking).length;
  return (
    <div className="restaurant-capability status-ready">
      <span aria-hidden="true" className="restaurant-capability__dot" />
      <span>
        <strong>{copy.uberUpdated}:</strong>{" "}
        {result.observed_count} {copy.uberDishes}
        {" · "}{nutritionReady} {copy.uberNutritionReady}
      </span>
    </div>
  );
}

function RestaurantSyncSummary({ result }: { result: RestaurantMenuSync }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const totalItems = result.menus.reduce((sum, menu) => sum + menu.items.length, 0);
  return (
    <div className="restaurant-capability status-ready">
      <span aria-hidden="true" className="restaurant-capability__dot" />
      <span>
        <strong>{copy.restaurantsUpdated}:</strong>{" "}
        {result.provider === "google_places" ? copy.sourceGoogle : copy.sourceOsm}
        {" · "}{result.menus.length} {copy.restaurantsAnalysed}
        {" · "}{totalItems} {copy.menuDishes}
        {" · "}{result.nutrition_ready_item_count} {copy.nutritionReady}
      </span>
    </div>
  );
}

export default function RecommendationPlanner({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const today = localDateValue();
  const [people, setPeople] = useState<Person[]>([]);
  const [discoveryByPersonId, setDiscoveryByPersonId] = useState<Record<string, PersonMealDiscovery>>({});
  const [selectedPersonIds, setSelectedPersonIds] = useState<string[]>([]);
  const [periodMode, setPeriodMode] = useState<RecommendationPeriodMode>("single");
  const [startDate, setStartDate] = useState(today);
  const [endDate, setEndDate] = useState(today);
  const [mealType, setMealType] = useState<RecommendationMealType>("lunch");
  const [localTime, setLocalTime] = useState(DEFAULT_MEAL_TIMES.lunch);
  const [sources, setSources] = useState<RecommendationSource[]>([]);
  const [location, setLocation] = useState("");
  const [availableMinutes, setAvailableMinutes] = useState("");
  const [results, setResults] = useState<DayResult[]>([]);
  const [decisions, setDecisions] = useState<Record<string, RecommendationDecision>>({});
  const [sharedPlans, setSharedPlans] = useState<Record<string, SharedPracticalPlan>>({});
  const [deliverySync, setDeliverySync] = useState<MealDeliverySync | null>(null);
  const [deliverySyncWarning, setDeliverySyncWarning] = useState<string | null>(null);
  const [menuSync, setMenuSync] = useState<RestaurantMenuSync | null>(null);
  const [menuSyncWarning, setMenuSyncWarning] = useState<string | null>(null);
  const [busy, setBusy] = useState<BusyState>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedPeople = useMemo(
    () => people.filter((person) => selectedPersonIds.includes(person.id)),
    [people, selectedPersonIds],
  );
  const peopleById = useMemo(
    () => new Map<string, Person>(people.map((person) => [person.id, person])),
    [people],
  );
  const configuredSources = useMemo(
    () => commonRecommendationSources(selectedPersonIds, discoveryByPersonId),
    [discoveryByPersonId, selectedPersonIds],
  );
  const allowedSources = useMemo(
    () => configuredSources.filter((source) => sourceSupportsMeal(source, mealType)),
    [configuredSources, mealType],
  );
  const allSelected = people.length > 0 && selectedPersonIds.length === people.length;

  useEffect(() => {
    let cancelled = false;
    void listFamilyPersons(familyId)
      .then(async (loaded) => {
        const discoveryPairs = await Promise.all(
          loaded.map(async (person) => [person.id, await getPersonMealDiscovery(person.id)] as const),
        );
        if (cancelled) return;
        const discovery = Object.fromEntries(discoveryPairs);
        const personIds = loaded.map((person) => person.id);
        setPeople(loaded);
        setDiscoveryByPersonId(discovery);
        setSelectedPersonIds(personIds);
      })
      .catch((caught: unknown) => {
        if (!cancelled) setError(errorText(caught));
      });
    return () => {
      cancelled = true;
    };
  }, [familyId]);

  useEffect(() => {
    setSources(allowedSources);
  }, [allowedSources]);

  function togglePerson(personId: string) {
    setSelectedPersonIds((current) =>
      current.includes(personId)
        ? current.filter((id) => id !== personId)
        : [...current, personId],
    );
  }

  function toggleAllPeople() {
    setSelectedPersonIds(allSelected ? [] : people.map((person) => person.id));
  }

  function toggleSource(source: RecommendationSource) {
    if (!allowedSources.includes(source)) return;
    setSources((current) =>
      current.includes(source)
        ? current.filter((item) => item !== source)
        : [...current, source],
    );
  }

  function changeMealType(value: RecommendationMealType) {
    setMealType(value);
    setLocalTime(DEFAULT_MEAL_TIMES[value]);
    setResults([]);
    setDeliverySync(null);
    setDeliverySyncWarning(null);
    setMenuSync(null);
    setMenuSyncWarning(null);
  }

  function parsedAvailableMinutes(): number | null {
    if (!availableMinutes.trim()) return null;
    const value = Number(availableMinutes);
    return Number.isFinite(value) ? value : null;
  }

  async function recommendDay(
    date: string,
    provisionalHistory: RecommendationHistoryHint[],
    activeSources: RecommendationSource[],
    resolvedRestaurantArea: string | null,
  ): Promise<DayResult> {
    const personIds = selectedPeople.map((person) => person.id);
    const mode = personIds.length === 1 ? "single" : "shared";
    const scheduledLocal = recommendationScheduledLocal(date, mealType, localTime);
    const scheduledAt = scheduledIso(scheduledLocal);
    const firstPerson = selectedPeople.at(0);
    const nutritionBudgets: RecommendationNutritionBudget[] = [];

    if (!firstPerson) {
      const base: DayResultBase = {
        date,
        scheduledLocal,
        personIds,
        sources: [...activeSources],
        nutritionBudgets,
        error: copy.peopleRequired,
      };
      return mode === "single"
        ? { ...base, mode, run: null, request: null }
        : { ...base, mode, run: null, request: null };
    }

    try {
      const personBootstraps = await Promise.all(
        selectedPeople.map(async (person) => ({
          person,
          bootstrap: await getRecommendationBootstrap(person.id, scheduledAt),
        })),
      );
      const firstPair = personBootstraps.at(0);
      if (!firstPair) throw new Error(copy.peopleRequired);
      const firstBootstrap = firstPair.bootstrap;

      nutritionBudgets.push(
        ...personBootstraps.map(({ person, bootstrap }) => {
          if (!bootstrap.daily_nutrition_state) {
            throw new Error(`${copy.stateUnavailable} ${displayName(person)}.`);
          }
          return recommendationNutritionBudget(person, bootstrap.daily_nutrition_state);
        }),
      );

      const firstState = firstBootstrap.daily_nutrition_state;
      if (!firstState) throw new Error(`${copy.stateUnavailable} ${displayName(firstPerson)}.`);
      const candidates = recommendationCandidates(
        firstBootstrap.candidates,
        activeSources,
        mealType,
      );

      if (candidates.length === 0) {
        const base: DayResultBase = {
          date,
          scheduledLocal,
          personIds,
          sources: [...activeSources],
          nutritionBudgets,
          error: copy.noCandidates,
        };
        return mode === "single"
          ? { ...base, mode, run: null, request: null }
          : { ...base, mode, run: null, request: null };
      }

      const recommendationLocation =
        location.trim() || (activeSources.includes("restaurant") ? resolvedRestaurantArea : null);
      const common = {
        planning_date: firstBootstrap.planning_date,
        scheduled_at: scheduledAt,
        meal_type: mealType,
        candidates,
        location: recommendationLocation,
        available_minutes: parsedAvailableMinutes(),
        has_kitchen: activeSources.includes("cooked") ? true : null,
        source_kinds: recommendationSourceKinds(activeSources),
        delivery_provider_keys: recommendationDeliveryProviderKeys(activeSources),
        provisional_history: [...provisionalHistory],
        auto_size_portions: true,
        max_results: MAX_VISIBLE_RESULTS,
      };

      if (mode === "single") {
        const request: PracticalRecommendationRequest = {
          daily_nutrition_state_id: firstState.id,
          ...common,
        };
        const run = await requestPracticalRecommendation(firstPerson.id, request);
        return {
          mode,
          date,
          scheduledLocal,
          personIds,
          sources: [...activeSources],
          nutritionBudgets,
          run,
          request,
          error: null,
        };
      }

      const request: SharedPracticalRecommendationRequest = {
        person_ids: personIds,
        ...common,
      };
      const run = await requestSharedPracticalRecommendation(familyId, request);
      return {
        mode,
        date,
        scheduledLocal,
        personIds,
        sources: [...activeSources],
        nutritionBudgets,
        run,
        request,
        error: null,
      };
    } catch (caught: unknown) {
      const base: DayResultBase = {
        date,
        scheduledLocal,
        personIds,
        sources: [...activeSources],
        nutritionBudgets,
        error: errorText(caught),
      };
      return mode === "single"
        ? { ...base, mode, run: null, request: null }
        : { ...base, mode, run: null, request: null };
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setDeliverySync(null);
    setDeliverySyncWarning(null);
    setMenuSync(null);
    setMenuSyncWarning(null);
    setDecisions({});
    setSharedPlans({});
    setResults([]);
    if (people.length === 0) {
      setError(copy.noPeople);
      return;
    }
    if (selectedPeople.length === 0) {
      setError(copy.peopleRequired);
      return;
    }
    if (sources.length === 0) {
      setError(copy.sourceRequired);
      return;
    }

    let dates: string[];
    try {
      dates = recommendationDates(periodMode, startDate, endDate);
    } catch (caught: unknown) {
      setError(errorText(caught));
      return;
    }

    setBusy({ kind: "recommend" });
    try {
      let activeSources = [...sources];
      let resolvedRestaurantArea: string | null = null;

      if (sources.includes("uber_eats")) {
        try {
          const synced = await syncMealDeliveryProvider(familyId, "uber_eats", undefined, 100);
          setDeliverySync(synced);
        } catch (caught: unknown) {
          setDeliverySyncWarning(`${copy.uberUnavailable} ${errorText(caught)}`);
        }
      }

      if (sources.includes("restaurant")) {
        const area = restaurantAreaForPeople(
          selectedPeople.map((person) => person.id),
          discoveryByPersonId,
          location,
        );
        if (area === null) {
          setError(copy.restaurantAreaRequired);
          return;
        }
        if (area === "mismatch") {
          setError(copy.restaurantAreaMismatch);
          return;
        }
        resolvedRestaurantArea = area;
        try {
          const synced = await syncRestaurantMenus(familyId, {
            area,
            restaurant_limit: RESTAURANT_LIMIT,
            item_limit_per_restaurant: 60,
          });
          setMenuSync(synced);
        } catch (caught: unknown) {
          activeSources = activeSources.filter((source) => source !== "restaurant");
          const detail = errorText(caught);
          setMenuSyncWarning(
            activeSources.length === 0
              ? `${copy.restaurantOnlyUnavailable} ${detail}`
              : `${copy.restaurantUnavailable} ${detail}`,
          );
          if (activeSources.length === 0) return;
        }
      }

      const nextResults: DayResult[] = [];
      let provisionalHistory: RecommendationHistoryHint[] = [];
      for (const date of dates) {
        const day = await recommendDay(
          date,
          provisionalHistory,
          activeSources,
          resolvedRestaurantArea,
        );
        nextResults.push(day);
        setResults([...nextResults]);
        const topKey = topCandidateKey(day);
        if (topKey) {
          provisionalHistory = [...provisionalHistory, { plan_date: date, candidate_key: topKey }];
        }
      }
    } finally {
      setBusy(null);
    }
  }

  async function decideSingle(
    day: SingleDayResult,
    option: RecommendationOption,
    action: "accepted" | "rejected",
  ) {
    const personId = day.personIds.at(0);
    const person = personId ? peopleById.get(personId) : undefined;
    if (!person) return;
    setBusy({ kind: "single-decision", optionId: option.id });
    setError(null);
    try {
      const decision = await submitRecommendationDecision(
        option.id,
        action === "accepted"
          ? {
              action,
              scheduled_at: scheduledIso(day.scheduledLocal),
              timezone: person.timezone,
              meal_type: mealType,
              location: day.request?.location ?? null,
              feedback_metadata: { entrypoint: "web-v2-smart-recommendation" },
            }
          : { action, feedback_metadata: { entrypoint: "web-v2-smart-recommendation" } },
      );
      setDecisions((current) => ({ ...current, [option.id]: decision }));
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(null);
    }
  }

  async function planShared(day: SharedDayResult, option: SharedRecommendationOption) {
    if (!day.request) return;
    const key = `${day.date}:${option.candidate_key}`;
    setBusy({ kind: "shared-plan", key });
    setError(null);
    try {
      const planned = await planSharedPracticalRecommendation(familyId, {
        ...day.request,
        candidate_key: option.candidate_key,
        title: option.candidate_name,
      });
      setSharedPlans((current) => ({ ...current, [key]: planned }));
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="recommend-planner">
      <section className="recommend-setup">
        <header className="screen-header compact-screen-header">
          <div>
            <span className="eyebrow">Recomendar</span>
            <h1>{copy.title}</h1>
            <p>{copy.help}</p>
          </div>
        </header>
        {error ? (
          <div className="error-banner" role="alert">
            <strong>{copy.error}</strong><span>{error}</span>
          </div>
        ) : null}
        <form className="stack" onSubmit={submit}>
          <div className="field-group recommend-people-group">
            <span className="field-group__label">{copy.people}</span>
            <div className="recommend-people-grid">
              <label className={`recommend-person-card recommend-person-card--all ${allSelected ? "selected" : ""}`}>
                <input checked={allSelected} onChange={toggleAllPeople} type="checkbox" />
                <strong>{copy.allPeople}</strong>
              </label>
              {people.map((person) => {
                const selected = selectedPersonIds.includes(person.id);
                return (
                  <label className={`recommend-person-card ${selected ? "selected" : ""}`} key={person.id}>
                    <input checked={selected} onChange={() => togglePerson(person.id)} type="checkbox" />
                    <strong>{displayName(person)}</strong>
                  </label>
                );
              })}
            </div>
          </div>

          <div className="recommend-primary-grid">
            <div className="field-group">
              <span className="field-group__label">{copy.period}</span>
              <div className="segmented-control">
                <button className={periodMode === "single" ? "active" : ""} onClick={() => setPeriodMode("single")} type="button">
                  {copy.single}
                </button>
                <button className={periodMode === "range" ? "active" : ""} onClick={() => setPeriodMode("range")} type="button">
                  {copy.range}
                </button>
              </div>
            </div>
            {periodMode === "single" ? (
              <label className="field">
                <span>{copy.date}</span>
                <input
                  type="date"
                  value={startDate}
                  onChange={(event) => {
                    setStartDate(event.target.value);
                    setEndDate(event.target.value);
                  }}
                />
              </label>
            ) : (
              <div className="recommend-date-range">
                <label className="field">
                  <span>{copy.startDate}</span>
                  <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
                </label>
                <label className="field">
                  <span>{copy.endDate}</span>
                  <input min={startDate} type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
                </label>
              </div>
            )}
            <label className="field">
              <span>{copy.mealType}</span>
              <select value={mealType} onChange={(event) => changeMealType(event.target.value as RecommendationMealType)}>
                {RECOMMENDATION_MEAL_TYPES.map((type) => (
                  <option key={type} value={type}>{copy[type]}</option>
                ))}
              </select>
            </label>
          </div>

          <div className="field-group">
            <span className="field-group__label">{copy.sources}</span>
            <div className="recommend-source-grid">
              {RECOMMENDATION_SOURCES.map((source) => (
                <SourceChoice
                  disabled={!allowedSources.includes(source)}
                  key={source}
                  onChange={() => toggleSource(source)}
                  selected={sources.includes(source)}
                  source={source}
                />
              ))}
            </div>
          </div>

          <details className="recommend-more">
            <summary>{copy.more}</summary>
            <div className="form-grid three">
              <label className="field">
                <span>{copy.time}</span>
                <input type="time" value={localTime} onChange={(event) => setLocalTime(event.target.value)} />
              </label>
              <label className="field">
                <span>{copy.location}</span>
                <input value={location} onChange={(event) => setLocation(event.target.value)} />
              </label>
              <label className="field">
                <span>{copy.minutes}</span>
                <input min="0" type="number" value={availableMinutes} onChange={(event) => setAvailableMinutes(event.target.value)} />
              </label>
            </div>
          </details>

          <button
            className="button primary large"
            disabled={busy?.kind === "recommend" || selectedPeople.length === 0}
            type="submit"
          >
            {busy?.kind === "recommend" ? copy.recommending : copy.recommend}
          </button>
        </form>
      </section>

      {deliverySync ? <DeliverySyncSummary result={deliverySync} /> : null}
      {deliverySyncWarning ? <div className="error-banner"><span>{deliverySyncWarning}</span></div> : null}
      {menuSync ? <RestaurantSyncSummary result={menuSync} /> : null}
      {menuSyncWarning ? <div className="error-banner"><span>{menuSyncWarning}</span></div> : null}

      {results.length > 0 ? (
        <section className="recommend-results">
          <div className="section-heading"><h2>{copy.results}</h2></div>
          <div className="recommend-day-list">
            {results.map((day) => {
              const optionCount = day.run
                ? day.mode === "single"
                  ? visibleSingleOptions(day.run, day.sources).length
                  : visibleSharedOptions(day.run, day.sources).length
                : 0;
              return (
                <section className="recommend-day" key={day.date}>
                  <div className="recommend-day__heading">
                    <h3>{formatDate(day.date, locale)}</h3>
                    <span>{copy[mealType]} · {localTime} · {day.personIds.length} {copy.peopleLower}</span>
                  </div>
                  <RecommendationNutritionBudgetPanel budgets={day.nutritionBudgets} />
                  {day.error ? <div className="error-banner"><span>{day.error}</span></div> : null}
                  {!day.error && day.run && optionCount === 0 ? (
                    <div className="empty-state compact-empty-state"><p>{copy.noResults}</p></div>
                  ) : null}
                  {day.mode === "single" && day.run ? (
                    <div className="recommendation-grid">
                      {visibleSingleOptions(day.run, day.sources).map((option) => (
                        <SingleResultCard
                          busy={busy?.kind === "single-decision" && busy.optionId === option.id}
                          decision={decisions[option.id]}
                          key={option.id}
                          onDecision={(selected, action) => void decideSingle(day, selected, action)}
                          option={option}
                          run={day.run as PracticalRecommendationRun}
                          sources={day.sources}
                        />
                      ))}
                    </div>
                  ) : null}
                  {day.mode === "shared" && day.run ? (
                    <div className="recommendation-grid">
                      {visibleSharedOptions(day.run, day.sources).map((option) => {
                        const key = `${day.date}:${option.candidate_key}`;
                        return (
                          <SharedResultCard
                            busy={busy?.kind === "shared-plan" && busy.key === key}
                            key={option.candidate_key}
                            onPlan={(selected) => void planShared(day, selected)}
                            option={option}
                            peopleById={peopleById}
                            planned={sharedPlans[key]}
                            run={day.run as SharedPracticalRecommendation}
                            sources={day.sources}
                          />
                        );
                      })}
                    </div>
                  ) : null}
                </section>
              );
            })}
          </div>
        </section>
      ) : null}
    </div>
  );
}
