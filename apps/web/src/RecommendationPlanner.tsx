import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  ApiError,
  listFamilyPersons,
  requestPracticalRecommendation,
  submitRecommendationDecision,
} from "./api/client";
import { getRecommendationBootstrap } from "./api/recommendationClient";
import type {
  CommercialOffer,
  Person,
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
    help: "Escolhe os dias, o tipo de refeição e onde queres procurar. O NutriFlow compara automaticamente as opções elegíveis.",
    person: "Pessoa",
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
  },
  en: {
    title: "Meal recommendations",
    help: "Choose the days, meal type and where to search. NutriFlow automatically compares eligible options.",
    person: "Person",
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
  },
} as const;

type DayResult = {
  date: string;
  scheduledLocal: string;
  run: PracticalRecommendationRun | null;
  error: string | null;
};

type BusyState = { kind: "recommend" } | { kind: "decision"; optionId: string } | null;

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
  run: PracticalRecommendationRun,
  option: RecommendationOption,
  sources: RecommendationSource[],
): CommercialOffer[] {
  const allowed = new Set<string>();
  if (sources.includes("delivery")) allowed.add("delivery");
  if (sources.includes("restaurant")) allowed.add("restaurant");
  return run.commercial_offers.filter(
    (offer) => offer.candidate_key === option.candidate_key && allowed.has(offer.source_kind),
  );
}

function visibleOptions(
  run: PracticalRecommendationRun,
  sources: RecommendationSource[],
): RecommendationOption[] {
  return run.options.filter((option) => {
    if (!option.eligible) return false;
    if (option.candidate_kind === "recipe" && sources.includes("cooked")) return true;
    return matchingOffers(run, option, sources).length > 0;
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
  const help = copy[`${source}Help` as "cookedHelp" | "deliveryHelp" | "restaurantHelp"];
  return (
    <label className={`recommend-source-card ${selected ? "selected" : ""}`}>
      <input checked={selected} onChange={onChange} type="checkbox" />
      <span><strong>{label}</strong><small>{help}</small></span>
    </label>
  );
}

function ResultCard({
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
  const offers = matchingOffers(run, option, sources);
  return (
    <article className="recommendation-card eligible">
      <div className="recommendation-card__header">
        <div>
          <span className="eyebrow">{option.rank !== null ? `#${option.rank}` : copy.results}</span>
          <h3>{option.candidate_name}</h3>
          <p className="muted compact">{formatNumber(option.quantity, locale)} {option.quantity_unit}</p>
        </div>
        {option.nutrition.energy_kcal !== null ? (
          <div className="energy-pill"><strong>{formatNumber(option.nutrition.energy_kcal, locale, 0)}</strong><span>kcal</span></div>
        ) : null}
      </div>
      {offers.length > 0 ? (
        <div className="detail-block">
          <span className="detail-label">{copy.from}</span>
          <div className="offer-list">
            {offers.map((offer) => (
              <div className="offer-row" key={offer.offer_key}>
                <div><strong>{offer.provider_name ?? offer.provider_key}</strong><span className="muted">{offer.source_kind}{offer.location ? ` · ${offer.location}` : ""}</span></div>
                <strong>{formatMoney(offer.total_known_price, offer.currency, locale)}</strong>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {option.explanation.length > 0 ? (
        <div className="detail-block"><ul className="compact-list">{option.explanation.slice(0, 3).map((message) => <li key={message}>{message}</li>)}</ul></div>
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

export default function RecommendationPlanner({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const today = localDateValue();
  const [people, setPeople] = useState<Person[]>([]);
  const [personId, setPersonId] = useState("");
  const [periodMode, setPeriodMode] = useState<RecommendationPeriodMode>("single");
  const [startDate, setStartDate] = useState(today);
  const [endDate, setEndDate] = useState(today);
  const [mealType, setMealType] = useState<RecommendationMealType>("lunch");
  const [localTime, setLocalTime] = useState(DEFAULT_MEAL_TIMES.lunch);
  const [sources, setSources] = useState<RecommendationSource[]>(["cooked", "delivery", "restaurant"]);
  const [location, setLocation] = useState("");
  const [availableMinutes, setAvailableMinutes] = useState("");
  const [results, setResults] = useState<DayResult[]>([]);
  const [decisions, setDecisions] = useState<Record<string, RecommendationDecision>>({});
  const [busy, setBusy] = useState<BusyState>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedPerson = useMemo(
    () => people.find((person) => person.id === personId) ?? null,
    [people, personId],
  );

  useEffect(() => {
    let cancelled = false;
    void listFamilyPersons(familyId)
      .then((loaded) => {
        if (cancelled) return;
        setPeople(loaded);
        setPersonId((current) => loaded.some((person) => person.id === current) ? current : (loaded[0]?.id ?? ""));
      })
      .catch((caught: unknown) => { if (!cancelled) setError(errorText(caught)); });
    return () => { cancelled = true; };
  }, [familyId]);

  function toggleSource(source: RecommendationSource) {
    setSources((current) => current.includes(source) ? current.filter((item) => item !== source) : [...current, source]);
  }

  function changeMealType(value: RecommendationMealType) {
    setMealType(value);
    setLocalTime(DEFAULT_MEAL_TIMES[value]);
  }

  async function recommendDay(date: string): Promise<DayResult> {
    if (!selectedPerson) throw new Error(copy.noPeople);
    const scheduledLocal = recommendationScheduledLocal(date, mealType, localTime);
    try {
      const scheduledAt = scheduledIso(scheduledLocal);
      const bootstrap = await getRecommendationBootstrap(selectedPerson.id, scheduledAt);
      if (!bootstrap.daily_nutrition_state) throw new Error("Daily nutrition state is unavailable.");
      const candidates = recommendationCandidates(bootstrap.candidates, sources);
      if (candidates.length === 0) return { date, scheduledLocal, run: null, error: copy.noCandidates };
      const parsedMinutes = availableMinutes.trim() ? Number(availableMinutes) : null;
      const run = await requestPracticalRecommendation(selectedPerson.id, {
        daily_nutrition_state_id: bootstrap.daily_nutrition_state.id,
        planning_date: bootstrap.planning_date,
        scheduled_at: scheduledAt,
        meal_type: mealType,
        candidates,
        location: location.trim() || null,
        available_minutes: parsedMinutes !== null && Number.isFinite(parsedMinutes) ? parsedMinutes : null,
        has_kitchen: sources.includes("cooked") ? true : null,
        source_kinds: recommendationSourceKinds(sources),
      });
      return { date, scheduledLocal, run, error: null };
    } catch (caught: unknown) {
      return { date, scheduledLocal, run: null, error: errorText(caught) };
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setDecisions({});
    if (!selectedPerson) { setError(copy.noPeople); return; }
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

  async function decide(day: DayResult, option: RecommendationOption, action: "accepted" | "rejected") {
    if (!selectedPerson) return;
    setBusy({ kind: "decision", optionId: option.id });
    setError(null);
    try {
      const decision = await submitRecommendationDecision(
        option.id,
        action === "accepted"
          ? {
              action,
              scheduled_at: scheduledIso(day.scheduledLocal),
              timezone: selectedPerson.timezone,
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

  return (
    <div className="recommend-planner">
      <section className="recommend-setup">
        <header className="screen-header compact-screen-header">
          <div><span className="eyebrow">Recomendar</span><h1>{copy.title}</h1><p>{copy.help}</p></div>
        </header>
        {error ? <div className="error-banner" role="alert"><strong>{copy.error}</strong><span>{error}</span></div> : null}
        <form className="stack" onSubmit={submit}>
          <div className="recommend-primary-grid">
            <label className="field">
              <span>{copy.person}</span>
              <select value={personId} onChange={(event) => setPersonId(event.target.value)}>
                {people.map((person) => <option key={person.id} value={person.id}>{displayName(person)}</option>)}
              </select>
            </label>
            <div className="field-group">
              <span className="field-group__label">Período</span>
              <div className="segmented-control">
                <button className={periodMode === "single" ? "active" : ""} onClick={() => setPeriodMode("single")} type="button">{copy.single}</button>
                <button className={periodMode === "range" ? "active" : ""} onClick={() => setPeriodMode("range")} type="button">{copy.range}</button>
              </div>
            </div>
            {periodMode === "single" ? (
              <label className="field"><span>{copy.date}</span><input type="date" value={startDate} onChange={(event) => { setStartDate(event.target.value); setEndDate(event.target.value); }} /></label>
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
              {RECOMMENDATION_SOURCES.map((source) => <SourceChoice key={source} onChange={() => toggleSource(source)} selected={sources.includes(source)} source={source} />)}
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

          <button className="button primary large" disabled={busy?.kind === "recommend" || !personId} type="submit">{busy?.kind === "recommend" ? copy.recommending : copy.recommend}</button>
        </form>
      </section>

      {results.length > 0 ? (
        <section className="recommend-results">
          <div className="section-heading"><h2>{copy.results}</h2></div>
          <div className="recommend-day-list">
            {results.map((day) => {
              const options = day.run ? visibleOptions(day.run, sources) : [];
              return (
                <section className="recommend-day" key={day.date}>
                  <div className="recommend-day__heading"><h3>{formatDate(day.date, locale)}</h3><span>{copy[mealType]} · {localTime}</span></div>
                  {day.error ? <div className="error-banner"><span>{day.error}</span></div> : null}
                  {!day.error && day.run && options.length === 0 ? <div className="empty-state compact-empty-state"><p>{copy.noResults}</p></div> : null}
                  {day.run && options.length > 0 ? (
                    <div className="recommendation-grid">
                      {options.map((option) => (
                        <ResultCard
                          busy={busy?.kind === "decision" && busy.optionId === option.id}
                          decision={decisions[option.id]}
                          key={option.id}
                          onDecision={(selected, action) => void decide(day, selected, action)}
                          option={option}
                          run={day.run as PracticalRecommendationRun}
                          sources={sources}
                        />
                      ))}
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
