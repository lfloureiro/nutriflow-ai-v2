import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  ApiError,
  listFamilyPersons,
  requestPracticalRecommendation,
  submitRecommendationDecision,
} from "./api/client";
import { getRecommendationBootstrap } from "./api/recommendationClient";
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
import type {
  CommercialOffer,
  Person,
  PracticalRecommendationRequest,
  PracticalRecommendationRun,
  RecommendationDecision,
  RecommendationOption,
} from "./api/types";
import { useI18n, type Locale } from "./i18n";
import { localDateValue, scheduledIso } from "./planning";
import {
  DEFAULT_MEAL_TIMES,
  RECOMMENDATION_MEAL_TYPES,
  RECOMMENDATION_SOURCES,
  recommendationCandidates,
  recommendationDates,
  recommendationScheduledLocal,
  recommendationSourceKinds,
  type RecommendationMealType,
  type RecommendationPeriodMode,
  type RecommendationSource,
} from "./recommendationPlanning";

const COPY = {
  "pt-PT": {
    title: "Recomendar refeições",
    help: "Escolhe quem vai comer, os dias, o tipo de refeição e onde queres procurar. O NutriFlow compara automaticamente as opções elegíveis.",
    people: "Pessoas",
    peopleLower: "pessoas",
    allPeople: "Todos",
    single: "1 dia",
    range: "Vários dias",
    date: "Dia",
    startDate: "De",
    endDate: "Até",
    mealType: "Tipo de refeição",
    sources: "Onde procurar",
    cooked: "Receitas / cozinhar",
    cookedHelp: "Refeições da lista de receitas da família",
    delivery: "Encomenda",
    deliveryHelp: "Opções disponíveis para entrega",
    restaurant: "Restaurante",
    restaurantHelp: "Opções disponíveis em restaurante",
    more: "Mais opções",
    time: "Hora",
    location: "Local",
    minutes: "Tempo disponível (min)",
    recommend: "Obter recomendações",
    recommending: "A calcular recomendações…",
    noPeople: "Não existem pessoas nesta família.",
    peopleRequired: "Escolhe pelo menos uma pessoa.",
    sourceRequired: "Escolhe pelo menos uma origem para a recomendação.",
    noCandidates: "Não existem refeições elegíveis no catálogo para as origens escolhidas.",
    noResults: "Não foram encontradas opções disponíveis para este dia e origem.",
    error: "Não foi possível obter a recomendação",
    results: "Recomendações",
    planned: "Adicionada ao plano",
    accept: "Adicionar ao plano",
    reject: "Rejeitar",
    breakfast: "Pequeno-almoço",
    lunch: "Almoço",
    snack: "Lanche",
    dinner: "Jantar",
    from: "Origem",
    groupFit: "Adequação do grupo",
    portion: "Porção",
  },
  en: {
    title: "Meal recommendations",
    help: "Choose who will eat, the days, meal type and where to search. NutriFlow automatically compares eligible options.",
    people: "People",
    peopleLower: "people",
    allPeople: "Everyone",
    single: "1 day",
    range: "Several days",
    date: "Day",
    startDate: "From",
    endDate: "To",
    mealType: "Meal type",
    sources: "Where to search",
    cooked: "Recipes / cook",
    cookedHelp: "Meals from the family's recipe list",
    delivery: "Delivery",
    deliveryHelp: "Options available for delivery",
    restaurant: "Restaurant",
    restaurantHelp: "Options available at restaurants",
    more: "More options",
    time: "Time",
    location: "Location",
    minutes: "Available time (min)",
    recommend: "Get recommendations",
    recommending: "Calculating recommendations…",
    noPeople: "There are no people in this family.",
    peopleRequired: "Choose at least one person.",
    sourceRequired: "Choose at least one recommendation source.",
    noCandidates: "There are no eligible catalogue meals for the selected sources.",
    noResults: "No available options were found for this day and source.",
    error: "The recommendation could not be created",
    results: "Recommendations",
    planned: "Added to plan",
    accept: "Add to plan",
    reject: "Reject",
    breakfast: "Breakfast",
    lunch: "Lunch",
    snack: "Snack",
    dinner: "Dinner",
    from: "Source",
    groupFit: "Group fit",
    portion: "Portion",
  },
} as const;

type DayResultBase = {
  date: string;
  scheduledLocal: string;
  personIds: string[];
  sources: RecommendationSource[];
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

function matchingOffers(
  offers: OfferLike[],
  candidateKey: string,
  sources: RecommendationSource[],
): OfferLike[] {
  const allowed = new Set<string>();
  if (sources.includes("delivery")) allowed.add("delivery");
  if (sources.includes("restaurant")) allowed.add("restaurant");
  return offers.filter(
    (offer) => offer.candidate_key === candidateKey && allowed.has(offer.source_kind),
  );
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

function SourceChoice({
  source,
  selected,
  onChange,
}: {
  source: RecommendationSource;
  selected: boolean;
  onChange: () => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const label = copy[source];
  const helpKey = `${source}Help` as "cookedHelp" | "deliveryHelp" | "restaurantHelp";
  return (
    <label className={`recommend-source-card ${selected ? "selected" : ""}`}>
      <input checked={selected} onChange={onChange} type="checkbox" />
      <span><strong>{label}</strong><small>{copy[helpKey]}</small></span>
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
                {offer.source_kind}{offer.location ? ` · ${offer.location}` : ""}
              </span>
            </div>
            <strong>{formatMoney(offer.total_known_price, offer.currency, locale)}</strong>
          </div>
        ))}
      </div>
    </div>
  );
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
    <article className="recommendation-card eligible">
      <div className="recommendation-card__header">
        <div>
          <span className="eyebrow">{option.rank !== null ? `#${option.rank}` : copy.results}</span>
          <h3>{option.candidate_name}</h3>
          <p className="muted compact">
            {formatNumber(option.quantity, locale)} {option.quantity_unit}
          </p>
        </div>
        {option.nutrition.energy_kcal !== null ? (
          <div className="energy-pill">
            <strong>{formatNumber(option.nutrition.energy_kcal, locale, 0)}</strong><span>kcal</span>
          </div>
        ) : null}
      </div>
      <OfferList offers={offers} />
      {option.explanation.length > 0 ? (
        <div className="detail-block">
          <ul className="compact-list">
            {option.explanation.slice(0, 3).map((message) => <li key={message}>{message}</li>)}
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
    <article className="recommendation-card eligible shared-recommendation-card">
      <div className="recommendation-card__header">
        <div>
          <span className="eyebrow">{option.rank !== null ? `#${option.rank}` : copy.results}</span>
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
              <strong>{person ? displayName(person) : participant.person_id}</strong>
              <span>
                {copy.portion}: {formatNumber(participant.quantity, locale)} {participant.quantity_unit}
                {participant.energy_kcal !== null
                  ? ` · ${formatNumber(participant.energy_kcal, locale, 0)} kcal`
                  : ""}
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
          <button className="button primary" disabled={busy} onClick={() => onPlan(option)} type="button">
            {copy.accept}
          </button>
        </div>
      )}
    </article>
  );
}

export default function RecommendationPlanner({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const today = localDateValue();
  const [people, setPeople] = useState<Person[]>([]);
  const [selectedPersonIds, setSelectedPersonIds] = useState<string[]>([]);
  const [periodMode, setPeriodMode] = useState<RecommendationPeriodMode>("single");
  const [startDate, setStartDate] = useState(today);
  const [endDate, setEndDate] = useState(today);
  const [mealType, setMealType] = useState<RecommendationMealType>("lunch");
  const [localTime, setLocalTime] = useState(DEFAULT_MEAL_TIMES.lunch);
  const [sources, setSources] = useState<RecommendationSource[]>([
    "cooked",
    "delivery",
    "restaurant",
  ]);
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
  const allSelected = people.length > 0 && selectedPersonIds.length === people.length;

  useEffect(() => {
    let cancelled = false;
    void listFamilyPersons(familyId)
      .then((loaded) => {
        if (cancelled) return;
        setPeople(loaded);
        setSelectedPersonIds(loaded.map((person) => person.id));
      })
      .catch((caught: unknown) => { if (!cancelled) setError(errorText(caught)); });
    return () => { cancelled = true; };
  }, [familyId]);

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
    setSources((current) =>
      current.includes(source)
        ? current.filter((item) => item !== source)
        : [...current, source],
    );
  }

  function changeMealType(value: RecommendationMealType) {
    setMealType(value);
    setLocalTime(DEFAULT_MEAL_TIMES[value]);
  }

  function parsedAvailableMinutes(): number | null {
    if (!availableMinutes.trim()) return null;
    const value = Number(availableMinutes);
    return Number.isFinite(value) ? value : null;
  }

  async function recommendDay(date: string): Promise<DayResult> {
    const personIds = selectedPeople.map((person) => person.id);
    const mode = personIds.length === 1 ? "single" : "shared";
    const scheduledLocal = recommendationScheduledLocal(date, mealType, localTime);
    const scheduledAt = scheduledIso(scheduledLocal);
    const firstPerson = selectedPeople.at(0);
    if (!firstPerson) {
      throw new Error(copy.peopleRequired);
    }

    try {
      const bootstrap = await getRecommendationBootstrap(firstPerson.id, scheduledAt);
      if (!bootstrap.daily_nutrition_state) {
        throw new Error("Daily nutrition state is unavailable.");
      }
      const candidates = recommendationCandidates(bootstrap.candidates, sources);
      if (candidates.length === 0) {
        const base = {
          date,
          scheduledLocal,
          personIds,
          sources: [...sources],
          error: copy.noCandidates,
        };
        return mode === "single"
          ? { ...base, mode, run: null, request: null }
          : { ...base, mode, run: null, request: null };
      }

      const common = {
        planning_date: bootstrap.planning_date,
        scheduled_at: scheduledAt,
        meal_type: mealType,
        candidates,
        location: location.trim() || null,
        available_minutes: parsedAvailableMinutes(),
        has_kitchen: sources.includes("cooked") ? true : null,
        source_kinds: recommendationSourceKinds(sources),
      };

      if (mode === "single") {
        const request: PracticalRecommendationRequest = {
          daily_nutrition_state_id: bootstrap.daily_nutrition_state.id,
          ...common,
        };
        const run = await requestPracticalRecommendation(firstPerson.id, request);
        return {
          mode,
          date,
          scheduledLocal,
          personIds,
          sources: [...sources],
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
        run,
        request,
        error: null,
      };
    } catch (caught: unknown) {
      const base = {
        date,
        scheduledLocal,
        personIds,
        sources: [...sources],
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
    if (people.length === 0) { setError(copy.noPeople); return; }
    if (selectedPeople.length === 0) { setError(copy.peopleRequired); return; }
    if (sources.length === 0) { setError(copy.sourceRequired); return; }

    let dates: string[];
    try {
      dates = recommendationDates(periodMode, startDate, endDate);
    } catch (caught: unknown) {
      setError(errorText(caught));
      return;
    }

    setBusy({ kind: "recommend" });
    try {
      setResults(await Promise.all(dates.map(recommendDay)));
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
              feedback_metadata: { entrypoint: "web-v2-multi-day-recommendation" },
            }
          : { action, feedback_metadata: { entrypoint: "web-v2-multi-day-recommendation" } },
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
          <div><span className="eyebrow">Recomendar</span><h1>{copy.title}</h1><p>{copy.help}</p></div>
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
              <span className="field-group__label">Período</span>
              <div className="segmented-control">
                <button className={periodMode === "single" ? "active" : ""} onClick={() => setPeriodMode("single")} type="button">{copy.single}</button>
                <button className={periodMode === "range" ? "active" : ""} onClick={() => setPeriodMode("range")} type="button">{copy.range}</button>
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
