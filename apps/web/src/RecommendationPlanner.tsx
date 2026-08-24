import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  ApiError,
  listFamilyPersons,
  requestPracticalRecommendation,
  submitRecommendationDecision,
} from "./api/client";
import { getRecommendationBootstrap } from "./api/recommendationClient";
import { discoverRestaurants } from "./api/restaurantDiscoveryClient";
import type { RestaurantDiscovery } from "./api/restaurantDiscoveryTypes";
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
const RESTAURANT_LIMIT = 12;
const MAIN_MEAL_TYPES = new Set<RecommendationMealType>(["lunch", "dinner"]);

const COPY = {
  "pt-PT": {
    title: "Recomendar refeições",
    help: "Escolhe quem vai comer, quando e onde procurar. As receitas e pratos são avaliados pelas necessidades nutricionais e preferências; os restaurantes usam descoberta live ordenada por sinais de qualidade quando disponíveis.",
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
    cookedHelp: "Receitas partilhadas e receitas próprias da família, filtradas para esta refeição",
    uber_eats: "Uber Eats",
    uber_eatsHelp: "Pratos sincronizados quando a integração consumer oficial estiver operacional",
    glovo: "Glovo",
    glovoHelp: "Pratos sincronizados quando existir acesso autorizado ao catálogo",
    bolt_food: "Bolt Food",
    bolt_foodHelp: "Pratos sincronizados quando existir acesso autorizado ao catálogo",
    restaurant: "Restaurantes",
    restaurantHelp: "Restaurantes live na área configurada; usado apenas em almoço e jantar",
    sourceUnavailable: "Não está disponível para esta refeição ou para todas as pessoas selecionadas",
    more: "Mais opções",
    time: "Hora",
    location: "Área / local (override opcional)",
    minutes: "Tempo disponível (min)",
    recommend: "Obter recomendações",
    recommending: "A calcular recomendações…",
    noPeople: "Não existem pessoas nesta família.",
    peopleRequired: "Escolhe pelo menos uma pessoa.",
    sourceRequired: "Escolhe pelo menos uma origem disponível.",
    noCandidates: "Não existem receitas ou pratos com dados suficientes para esta refeição.",
    noResults: "Não foram encontradas receitas ou pratos adequados para este dia.",
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
    from: "Origem",
    deliverySource: "Entrega",
    groupFit: "Adequação do grupo",
    portion: "Porção",
    restaurants: "Restaurantes na área",
    restaurantLiveNote: "Descoberta live ordenada por qualidade/reputação quando o Google Places está configurado. A adequação nutricional continua a depender de um prato/menu concreto.",
    restaurantAreaRequired: "Configura uma área de restaurantes em Casa → Fontes ou indica uma área em Mais opções.",
    restaurantAreaMismatch: "As pessoas selecionadas têm áreas de restaurantes diferentes. Indica uma área comum em Mais opções.",
    restaurantUnavailable: "Não foi possível pesquisar restaurantes nesta área.",
    cuisine: "Cozinha",
    address: "Morada",
    openingHours: "Horário",
    website: "Site",
    ratings: "avaliações",
    price: "Preço",
  },
  en: {
    title: "Meal recommendations",
    help: "Choose who will eat, when and where to search. Recipes and dishes are evaluated against nutrition needs and preferences; restaurants use live discovery ranked by quality signals when available.",
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
    cookedHelp: "Shared and Family recipes filtered for this meal",
    uber_eats: "Uber Eats",
    uber_eatsHelp: "Synchronized dishes when the official consumer integration is operational",
    glovo: "Glovo",
    glovoHelp: "Synchronized dishes when authorized catalogue access is available",
    bolt_food: "Bolt Food",
    bolt_foodHelp: "Synchronized dishes when authorized catalogue access is available",
    restaurant: "Restaurants",
    restaurantHelp: "Live restaurants in the configured area; lunch and dinner only",
    sourceUnavailable: "Not available for this meal or every selected person",
    more: "More options",
    time: "Time",
    location: "Area / location (optional override)",
    minutes: "Available time (min)",
    recommend: "Get recommendations",
    recommending: "Calculating recommendations…",
    noPeople: "There are no people in this Family.",
    peopleRequired: "Choose at least one person.",
    sourceRequired: "Choose at least one available source.",
    noCandidates: "There are no recipes or dishes with enough data for this meal.",
    noResults: "No suitable recipes or dishes were found for this day.",
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
    from: "Source",
    deliverySource: "Delivery",
    groupFit: "Group fit",
    portion: "Portion",
    restaurants: "Restaurants in the area",
    restaurantLiveNote: "Live discovery is ranked by quality/reputation when Google Places is configured. Nutritional suitability still requires a concrete dish/menu item.",
    restaurantAreaRequired: "Configure a restaurant area under Home base → Sources or enter an area in More options.",
    restaurantAreaMismatch: "The selected people have different restaurant areas. Enter one common area in More options.",
    restaurantUnavailable: "Restaurants could not be searched in this area.",
    cuisine: "Cuisine",
    address: "Address",
    openingHours: "Opening hours",
    website: "Website",
    ratings: "ratings",
    price: "Price",
  },
} as const;

type DayResultBase = {
  date: string;
  scheduledLocal: string;
  personIds: string[];
  sources: RecommendationSource[];
  nutritionBudgets: RecommendationNutritionBudget[];
  restaurants: RestaurantDiscovery | null;
  restaurantError: string | null;
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
  if (source === "restaurant") return MAIN_MEAL_TYPES.has(mealType);
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
    if (offer.candidate_key !== candidateKey || offer.source_kind !== "delivery") return false;
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
    if (option.candidate_kind === "recipe" && sources.includes("cooked")) return true;
    return matchingOffers(run.commercial_offers, option.candidate_key, sources).length > 0;
  });
}

function visibleSharedOptions(
  run: SharedPracticalRecommendation,
  sources: RecommendationSource[],
): SharedRecommendationOption[] {
  return run.options.filter((option) => {
    if (!option.eligible) return false;
    if (option.candidate_kind === "recipe" && sources.includes("cooked")) return true;
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
                {copy.deliverySource}{offer.location ? ` · ${offer.location}` : ""}
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
          <p className="muted compact">{formatNumber(option.quantity, locale)} {option.quantity_unit}</p>
        </div>
        {option.nutrition.energy_kcal !== null ? (
          <div className="energy-pill"><strong>{formatNumber(option.nutrition.energy_kcal, locale, 0)}</strong><span>kcal</span></div>
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
        <div className="decision-result" role="status"><strong>{decision.action === "accepted" ? copy.planned : copy.reject}</strong></div>
      ) : (
        <div className="button-row">
          <button className="button primary" disabled={busy} onClick={() => onDecision(option, "accepted")} type="button">{copy.accept}</button>
          <button className="button ghost" disabled={busy} onClick={() => onDecision(option, "rejected")} type="button">{copy.reject}</button>
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
            {option.average_score !== null ? ` · ${copy.groupFit}: ${formatNumber(option.average_score, locale, 2)}` : ""}
          </p>
        </div>
      </div>
      <div className="shared-participant-list">
        {option.participants.map((participant) => {
          const person = peopleById.get(participant.person_id);
          return (
            <div className="shared-participant-row" key={participant.person_id}>
              <strong>{person ? displayName(person) : participant.person_id}</strong>
              <span>
                {copy.portion}: {formatNumber(participant.quantity, locale)} {participant.quantity_unit}
                {participant.energy_kcal !== null ? ` · ${formatNumber(participant.energy_kcal, locale, 0)} kcal` : ""}
              </span>
            </div>
          );
        })}
      </div>
      <OfferList offers={offers} />
      {planned ? (
        <div className="decision-result" role="status"><strong>{copy.planned}</strong></div>
      ) : (
        <div className="button-row">
          <button className="button primary" disabled={busy} onClick={() => onPlan(option)} type="button">{copy.accept}</button>
        </div>
      )}
    </article>
  );
}

function RestaurantResults({ result }: { result: RestaurantDiscovery }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  return (
    <section className="restaurant-results">
      <div className="section-heading">
        <div>
          <h3>{copy.restaurants}</h3>
          <p>{result.area} · {copy.restaurantLiveNote}</p>
        </div>
      </div>
      <div className="recommendation-grid">
        {result.restaurants.map((restaurant) => (
          <article className="recommendation-card eligible" key={restaurant.provider_place_id}>
            <div className="recommendation-card__header">
              <div>
                <span className="eyebrow">Live · {result.provider}</span>
                <h3>{restaurant.name}</h3>
                {restaurant.rating ? (
                  <p className="muted compact">
                    ★ {Number(restaurant.rating).toLocaleString(locale, {
                      minimumFractionDigits: 1,
                      maximumFractionDigits: 1,
                    })}
                    {restaurant.rating_count !== null
                      ? ` · ${new Intl.NumberFormat(locale).format(restaurant.rating_count)} ${copy.ratings}`
                      : ""}
                    {restaurant.price_level ? ` · ${copy.price}: ${restaurant.price_level}` : ""}
                  </p>
                ) : null}
              </div>
            </div>
            {restaurant.cuisine.length > 0 ? <p><strong>{copy.cuisine}:</strong> {restaurant.cuisine.join(", ")}</p> : null}
            {restaurant.address ? <p><strong>{copy.address}:</strong> {restaurant.address}</p> : null}
            {restaurant.opening_hours ? <p><strong>{copy.openingHours}:</strong> {restaurant.opening_hours}</p> : null}
            {restaurant.website ? <a href={restaurant.website} rel="noreferrer" target="_blank">{copy.website} ↗</a> : null}
          </article>
        ))}
      </div>
    </section>
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
  }

  function parsedAvailableMinutes(): number | null {
    if (!availableMinutes.trim()) return null;
    const value = Number(availableMinutes);
    return Number.isFinite(value) ? value : null;
  }

  async function discoverRestaurantOptions(personIds: string[]): Promise<{
    result: RestaurantDiscovery | null;
    error: string | null;
  }> {
    if (!sources.includes("restaurant")) return { result: null, error: null };
    const area = restaurantAreaForPeople(personIds, discoveryByPersonId, location);
    if (area === null) return { result: null, error: copy.restaurantAreaRequired };
    if (area === "mismatch") return { result: null, error: copy.restaurantAreaMismatch };
    try {
      return { result: await discoverRestaurants(familyId, area, RESTAURANT_LIMIT), error: null };
    } catch (caught: unknown) {
      return { result: null, error: `${copy.restaurantUnavailable} ${errorText(caught)}` };
    }
  }

  async function recommendDay(
    date: string,
    provisionalHistory: RecommendationHistoryHint[],
  ): Promise<DayResult> {
    const personIds = selectedPeople.map((person) => person.id);
    const mode = personIds.length === 1 ? "single" : "shared";
    const scheduledLocal = recommendationScheduledLocal(date, mealType, localTime);
    const scheduledAt = scheduledIso(scheduledLocal);
    const firstPerson = selectedPeople.at(0);
    if (!firstPerson) throw new Error(copy.peopleRequired);

    let nutritionBudgets: RecommendationNutritionBudget[] = [];
    const restaurantPromise = discoverRestaurantOptions(personIds);
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

      nutritionBudgets = personBootstraps.map(({ person, bootstrap }) => {
        if (!bootstrap.daily_nutrition_state) {
          throw new Error(`${copy.stateUnavailable} ${displayName(person)}.`);
        }
        return recommendationNutritionBudget(person, bootstrap.daily_nutrition_state);
      });

      const firstState = firstBootstrap.daily_nutrition_state;
      if (!firstState) throw new Error(`${copy.stateUnavailable} ${displayName(firstPerson)}.`);
      const candidates = recommendationCandidates(firstBootstrap.candidates, sources, mealType);
      const restaurants = await restaurantPromise;

      if (candidates.length === 0) {
        const base: DayResultBase = {
          date,
          scheduledLocal,
          personIds,
          sources: [...sources],
          nutritionBudgets,
          restaurants: restaurants.result,
          restaurantError: restaurants.error,
          error: sources.includes("restaurant") ? null : copy.noCandidates,
        };
        return mode === "single"
          ? { ...base, mode, run: null, request: null }
          : { ...base, mode, run: null, request: null };
      }

      const common = {
        planning_date: firstBootstrap.planning_date,
        scheduled_at: scheduledAt,
        meal_type: mealType,
        candidates,
        location: location.trim() || null,
        available_minutes: parsedAvailableMinutes(),
        has_kitchen: sources.includes("cooked") ? true : null,
        source_kinds: recommendationSourceKinds(sources),
        delivery_provider_keys: recommendationDeliveryProviderKeys(sources),
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
          sources: [...sources],
          nutritionBudgets,
          restaurants: restaurants.result,
          restaurantError: restaurants.error,
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
        sources: [...sources],
        nutritionBudgets,
        restaurants: restaurants.result,
        restaurantError: restaurants.error,
        run,
        request,
        error: null,
      };
    } catch (caught: unknown) {
      const restaurants = await restaurantPromise;
      const base: DayResultBase = {
        date,
        scheduledLocal,
        personIds,
        sources: [...sources],
        nutritionBudgets,
        restaurants: restaurants.result,
        restaurantError: restaurants.error,
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
      const nextResults: DayResult[] = [];
      let provisionalHistory: RecommendationHistoryHint[] = [];
      for (const date of dates) {
        const day = await recommendDay(date, provisionalHistory);
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
              location: location.trim() || null,
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
          <div className="error-banner" role="alert"><strong>{copy.error}</strong><span>{error}</span></div>
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
                <button className={periodMode === "single" ? "active" : ""} onClick={() => setPeriodMode("single")} type="button">{copy.single}</button>
                <button className={periodMode === "range" ? "active" : ""} onClick={() => setPeriodMode("range")} type="button">{copy.range}</button>
              </div>
            </div>
            {periodMode === "single" ? (
              <label className="field">
                <span>{copy.date}</span>
                <input type="date" value={startDate} onChange={(event) => { setStartDate(event.target.value); setEndDate(event.target.value); }} />
              </label>
            ) : (
              <div className="recommend-date-range">
                <label className="field"><span>{copy.startDate}</span><input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label>
                <label className="field"><span>{copy.endDate}</span><input min={startDate} type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} /></label>
              </div>
            )}
            <label className="field">
              <span>{copy.mealType}</span>
              <select value={mealType} onChange={(event) => changeMealType(event.target.value as RecommendationMealType)}>
                {RECOMMENDATION_MEAL_TYPES.map((type) => <option key={type} value={type}>{copy[type]}</option>)}
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
              <label className="field"><span>{copy.time}</span><input type="time" value={localTime} onChange={(event) => setLocalTime(event.target.value)} /></label>
              <label className="field"><span>{copy.location}</span><input value={location} onChange={(event) => setLocation(event.target.value)} /></label>
              <label className="field"><span>{copy.minutes}</span><input min="0" type="number" value={availableMinutes} onChange={(event) => setAvailableMinutes(event.target.value)} /></label>
            </div>
          </details>

          <button className="button primary large" disabled={busy?.kind === "recommend" || selectedPeople.length === 0} type="submit">
            {busy?.kind === "recommend" ? copy.recommending : copy.recommend}
          </button>
        </form>
      </section>

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
                  {day.restaurantError ? <div className="error-banner"><span>{day.restaurantError}</span></div> : null}
                  {day.restaurants ? <RestaurantResults result={day.restaurants} /> : null}
                </section>
              );
            })}
          </div>
        </section>
      ) : null}
    </div>
  );
}
