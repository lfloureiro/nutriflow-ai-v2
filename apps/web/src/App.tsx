import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  ApiError,
  getPlanningBootstrap,
  listFamilyPersons,
  requestPracticalRecommendation,
  submitRecommendationDecision,
} from "./api/client";
import type {
  Person,
  PlanningBootstrap,
  PlanningCandidate,
  PracticalRecommendationRun,
  PracticalSourceKind,
  RecommendationDecision,
  RecommendationOption,
} from "./api/types";
import { useI18n, type Locale } from "./i18n";
import {
  DEFAULT_SOURCE_KINDS,
  candidateDraftFromBootstrap,
  candidatePayload,
  hasCandidateValue,
  localDateTimeValue,
  newCandidateDraft,
  scheduledIso,
  type CandidateDraft,
} from "./planning";
import { useTheme, type Appearance } from "./theme";

const SOURCE_KINDS: PracticalSourceKind[] = [
  "home",
  "pantry",
  "restaurant",
  "delivery",
  "store",
];

type KitchenState = "unknown" | "yes" | "no";

type BusyState =
  | { kind: "people" }
  | { kind: "recommendation" }
  | { kind: "decision"; optionId: string }
  | null;

function displayName(person: Person): string {
  return [person.first_name, person.last_name].filter(Boolean).join(" ");
}

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.message} (HTTP ${error.status})`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

function kitchenValue(value: KitchenState): boolean | null {
  if (value === "yes") {
    return true;
  }
  if (value === "no") {
    return false;
  }
  return null;
}

function formatNumber(value: string, locale: Locale, maximumFractionDigits = 2): string {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return value;
  }
  return new Intl.NumberFormat(locale, { maximumFractionDigits }).format(number);
}

function formatMoney(value: string, currency: string, locale: Locale): string {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return `${value} ${currency}`;
  }
  try {
    return new Intl.NumberFormat(locale, { style: "currency", currency }).format(number);
  } catch {
    return `${formatNumber(value, locale)} ${currency}`;
  }
}

function candidateLabel(candidate: PlanningCandidate, locale: Locale): string {
  const parts = [candidate.name];
  if (candidate.brand) {
    parts.push(candidate.brand);
  }
  parts.push(`${formatNumber(candidate.reference_quantity, locale)} ${candidate.reference_unit}`);
  if (candidate.energy_kcal !== null) {
    parts.push(`${formatNumber(candidate.energy_kcal, locale, 0)} kcal`);
  }
  return parts.join(" · ");
}

function RecommendationCard({
  option,
  recommendation,
  decision,
  decisionBusy,
  onDecision,
}: {
  option: RecommendationOption;
  recommendation: PracticalRecommendationRun;
  decision: RecommendationDecision | undefined;
  decisionBusy: boolean;
  onDecision: (option: RecommendationOption, action: "accepted" | "rejected") => void;
}) {
  const { locale, t } = useI18n();
  const offers = recommendation.commercial_offers.filter(
    (offer) => offer.candidate_key === option.candidate_key,
  );
  const nutrients = Object.entries(option.nutrition.nutrients).slice(0, 4);

  return (
    <article className={`recommendation-card ${option.eligible ? "eligible" : "excluded"}`}>
      <div className="recommendation-card__header">
        <div>
          <div className="eyebrow">
            {option.eligible ? t("results.eligible") : t("results.excluded")}
            {option.rank !== null ? ` · #${option.rank}` : ""}
          </div>
          <h3>{option.candidate_name}</h3>
          <p className="muted">
            {formatNumber(option.quantity, locale)} {option.quantity_unit}
          </p>
        </div>
        {option.nutrition.energy_kcal !== null ? (
          <div className="energy-pill">
            <strong>{formatNumber(option.nutrition.energy_kcal, locale, 0)}</strong>
            <span>{t("results.kcal")}</span>
          </div>
        ) : null}
      </div>

      {nutrients.length > 0 ? (
        <div className="detail-block">
          <span className="detail-label">{t("results.nutrients")}</span>
          <div className="chip-row">
            {nutrients.map(([key, nutrient]) => (
              <span className="chip" key={key}>
                {key}: {formatNumber(nutrient.value, locale)} {nutrient.unit}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {option.explanation.length > 0 ? (
        <div className="detail-block">
          <span className="detail-label">{t("results.explanation")}</span>
          <ul className="compact-list">
            {option.explanation.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {option.exclusion_reasons.length > 0 ? (
        <div className="detail-block danger-block">
          <span className="detail-label">{t("results.reasons")}</span>
          <div className="chip-row">
            {option.exclusion_reasons.map((reason) => (
              <span className="chip danger" key={reason}>
                {reason}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {option.eligible ? (
        <div className="detail-block">
          <span className="detail-label">{t("results.offers")}</span>
          {offers.length > 0 ? (
            <div className="offer-list">
              {offers.map((offer) => (
                <div className="offer-row" key={offer.offer_key}>
                  <div>
                    <strong>{offer.provider_name ?? offer.provider_key}</strong>
                    <span className="muted">
                      {offer.source_kind}
                      {offer.location ? ` · ${offer.location}` : ""}
                    </span>
                  </div>
                  <div className="offer-price">
                    <span>{t("results.total")}</span>
                    <strong>
                      {formatMoney(offer.total_known_price, offer.currency, locale)}
                    </strong>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted compact">{t("results.noOffers")}</p>
          )}
        </div>
      ) : null}

      {decision ? (
        <div className="decision-result" role="status">
          <strong>
            {decision.action === "accepted" ? t("results.accepted") : t("results.rejected")}
          </strong>
          {decision.meal_event_id ? <span>{t("results.mealCreated")}</span> : null}
        </div>
      ) : option.eligible ? (
        <div className="button-row">
          <button
            className="button primary"
            disabled={decisionBusy}
            onClick={() => onDecision(option, "accepted")}
            type="button"
          >
            {decisionBusy ? t("status.savingDecision") : t("results.accept")}
          </button>
          <button
            className="button ghost"
            disabled={decisionBusy}
            onClick={() => onDecision(option, "rejected")}
            type="button"
          >
            {t("results.reject")}
          </button>
        </div>
      ) : null}
    </article>
  );
}

export default function App() {
  const { locale, setLocale, t } = useI18n();
  const { appearance, setAppearance } = useTheme();

  const [familyId, setFamilyId] = useState("");
  const [people, setPeople] = useState<Person[]>([]);
  const [personId, setPersonId] = useState("");
  const [scheduledLocal, setScheduledLocal] = useState(localDateTimeValue);
  const [mealType, setMealType] = useState("lunch");
  const [location, setLocation] = useState("");
  const [availableMinutes, setAvailableMinutes] = useState("30");
  const [kitchen, setKitchen] = useState<KitchenState>("unknown");
  const [sourceKinds, setSourceKinds] = useState<PracticalSourceKind[]>([
    ...DEFAULT_SOURCE_KINDS,
  ]);
  const [bootstrap, setBootstrap] = useState<PlanningBootstrap | null>(null);
  const [bootstrapBusy, setBootstrapBusy] = useState(false);
  const [candidates, setCandidates] = useState<CandidateDraft[]>([]);
  const [recommendation, setRecommendation] = useState<PracticalRecommendationRun | null>(
    null,
  );
  const [decisions, setDecisions] = useState<Record<string, RecommendationDecision>>({});
  const [busy, setBusy] = useState<BusyState>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedPerson = useMemo(
    () => people.find((person) => person.id === personId) ?? null,
    [people, personId],
  );

  useEffect(() => {
    let cancelled = false;
    setBootstrap(null);
    setCandidates([]);
    setRecommendation(null);
    setDecisions({});

    if (!selectedPerson) {
      setBootstrapBusy(false);
      return () => {
        cancelled = true;
      };
    }

    let scheduledAt: string;
    try {
      scheduledAt = scheduledIso(scheduledLocal);
    } catch (caught) {
      setError(errorText(caught));
      setBootstrapBusy(false);
      return () => {
        cancelled = true;
      };
    }

    setError(null);
    setBootstrapBusy(true);
    void getPlanningBootstrap(selectedPerson.id, scheduledAt)
      .then((result) => {
        if (cancelled) {
          return;
        }
        setBootstrap(result);
        const firstCandidate = result.candidates[0];
        setCandidates(
          firstCandidate ? [candidateDraftFromBootstrap(firstCandidate, "candidate-1")] : [],
        );
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(errorText(caught));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setBootstrapBusy(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [scheduledLocal, selectedPerson]);

  async function handleLoadPeople(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!familyId.trim()) {
      setError(t("validation.familyRequired"));
      return;
    }

    setBusy({ kind: "people" });
    try {
      const result = await listFamilyPersons(familyId.trim());
      setPeople(result);
      setPersonId((current) =>
        result.some((person) => person.id === current) ? current : (result[0]?.id ?? ""),
      );
      setRecommendation(null);
      setDecisions({});
    } catch (caught) {
      setError(errorText(caught));
    } finally {
      setBusy(null);
    }
  }

  function toggleSource(source: PracticalSourceKind) {
    setSourceKinds((current) => {
      if (current.includes(source)) {
        return current.length === 1 ? current : current.filter((item) => item !== source);
      }
      return [...current, source];
    });
  }

  function updateCandidate(rowId: string, patch: Partial<CandidateDraft>) {
    setCandidates((current) =>
      current.map((candidate) =>
        candidate.rowId === rowId ? { ...candidate, ...patch, rowId } : candidate,
      ),
    );
  }

  function selectCandidate(rowId: string, compositionId: string) {
    if (!bootstrap || compositionId === "") {
      updateCandidate(rowId, { composition_id: "" });
      return;
    }
    const selected = bootstrap.candidates.find(
      (candidate) => candidate.composition_id === compositionId,
    );
    if (!selected) {
      updateCandidate(rowId, { composition_id: "" });
      return;
    }
    setCandidates((current) =>
      current.map((candidate) =>
        candidate.rowId === rowId ? candidateDraftFromBootstrap(selected, rowId) : candidate,
      ),
    );
  }

  async function handleRecommend(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!selectedPerson) {
      setError(t("validation.personRequired"));
      return;
    }
    if (!bootstrap || bootstrapBusy) {
      setError(t("validation.contextRequired"));
      return;
    }
    if (!bootstrap.daily_nutrition_state) {
      setError(t("validation.stateRequired"));
      return;
    }

    const payloadCandidates = candidates.map(candidatePayload);
    if (payloadCandidates.length === 0) {
      setError(t("validation.candidateRequired"));
      return;
    }
    if (!payloadCandidates.every(hasCandidateValue)) {
      setError(t("validation.compositionRequired"));
      return;
    }

    const parsedMinutes = availableMinutes.trim() === "" ? null : Number(availableMinutes);
    setBusy({ kind: "recommendation" });
    try {
      const result = await requestPracticalRecommendation(selectedPerson.id, {
        daily_nutrition_state_id: bootstrap.daily_nutrition_state.id,
        planning_date: bootstrap.planning_date,
        scheduled_at: scheduledIso(scheduledLocal),
        meal_type: mealType.trim() || null,
        candidates: payloadCandidates,
        location: location.trim() || null,
        available_minutes:
          parsedMinutes !== null && Number.isFinite(parsedMinutes) ? parsedMinutes : null,
        has_kitchen: kitchenValue(kitchen),
        source_kinds: sourceKinds,
      });
      setRecommendation(result);
      setDecisions({});
    } catch (caught) {
      setError(errorText(caught));
    } finally {
      setBusy(null);
    }
  }

  async function handleDecision(
    option: RecommendationOption,
    action: "accepted" | "rejected",
  ) {
    if (!selectedPerson) {
      return;
    }
    setError(null);
    setBusy({ kind: "decision", optionId: option.id });
    try {
      const result = await submitRecommendationDecision(
        option.id,
        action === "accepted"
          ? {
              action,
              scheduled_at: scheduledIso(scheduledLocal),
              timezone: selectedPerson.timezone,
              meal_type: mealType.trim() || null,
              location: location.trim() || null,
              feedback_metadata: { entrypoint: "web-v2-bootstrap" },
            }
          : {
              action,
              feedback_metadata: { entrypoint: "web-v2-bootstrap" },
            },
      );
      setDecisions((current) => ({ ...current, [option.id]: result }));
    } catch (caught) {
      setError(errorText(caught));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="app-frame">
      <header className="topbar">
        <a className="brand" href="#top" aria-label={t("app.brand")}>
          <span className="brand-mark" aria-hidden="true">
            N
          </span>
          <span>{t("app.brand")}</span>
        </a>
        <div className="topbar-controls">
          <label className="compact-control">
            <span>{t("nav.language")}</span>
            <select value={locale} onChange={(event) => setLocale(event.target.value as Locale)}>
              <option value="pt-PT">PT</option>
              <option value="en">EN</option>
            </select>
          </label>
          <label className="compact-control">
            <span>{t("nav.appearance")}</span>
            <select
              value={appearance}
              onChange={(event) => setAppearance(event.target.value as Appearance)}
            >
              <option value="system">{t("theme.system")}</option>
              <option value="light">{t("theme.light")}</option>
              <option value="dark">{t("theme.dark")}</option>
            </select>
          </label>
        </div>
      </header>

      <main className="page-shell" id="top">
        <section className="hero">
          <div className="hero-copy">
            <span className="eyebrow">{t("app.brand")}</span>
            <h1>{t("app.tagline")}</h1>
          </div>
          {selectedPerson ? (
            <div className="person-chip">
              <span className="person-avatar">{selectedPerson.first_name.slice(0, 1)}</span>
              <div>
                <strong>{displayName(selectedPerson)}</strong>
                <span>{selectedPerson.timezone}</span>
              </div>
            </div>
          ) : null}
        </section>

        {error ? (
          <div className="error-banner" role="alert">
            <strong>{t("error.title")}</strong>
            <span>{error}</span>
          </div>
        ) : null}

        <div className="workflow-grid">
          <section className="panel setup-panel">
            <div className="section-heading">
              <div>
                <span className="section-number">01</span>
                <h2>{t("setup.title")}</h2>
              </div>
              <p>{t("setup.help")}</p>
            </div>

            <form className="stack" onSubmit={handleLoadPeople}>
              <label className="field">
                <span>{t("setup.familyId")}</span>
                <input
                  autoComplete="off"
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  value={familyId}
                  onChange={(event) => setFamilyId(event.target.value)}
                />
              </label>
              <button className="button secondary" disabled={busy?.kind === "people"} type="submit">
                {busy?.kind === "people" ? t("status.loadingPeople") : t("setup.loadPeople")}
              </button>
              <label className="field">
                <span>{t("setup.person")}</span>
                <select
                  disabled={people.length === 0}
                  value={personId}
                  onChange={(event) => setPersonId(event.target.value)}
                >
                  <option value="">{t("setup.choosePerson")}</option>
                  {people.map((person) => (
                    <option key={person.id} value={person.id}>
                      {displayName(person)}
                    </option>
                  ))}
                </select>
              </label>
            </form>
          </section>

          <section className="panel planner-panel">
            <div className="section-heading">
              <div>
                <span className="section-number">02</span>
                <h2>{t("planner.title")}</h2>
              </div>
              <p>{t("planner.help")}</p>
            </div>

            <form className="stack" onSubmit={handleRecommend}>
              <fieldset className="stack borderless" disabled={!selectedPerson}>
                <div className="form-grid three">
                  <label className="field">
                    <span>{t("planner.time")}</span>
                    <input
                      type="datetime-local"
                      value={scheduledLocal}
                      onChange={(event) => setScheduledLocal(event.target.value)}
                    />
                  </label>
                  <label className="field">
                    <span>{t("planner.mealType")}</span>
                    <input value={mealType} onChange={(event) => setMealType(event.target.value)} />
                  </label>
                  <label className="field">
                    <span>{t("planner.location")}</span>
                    <input value={location} onChange={(event) => setLocation(event.target.value)} />
                  </label>
                </div>

                {bootstrapBusy ? (
                  <div className="context-card" role="status">
                    <strong>{t("status.loadingContext")}</strong>
                  </div>
                ) : bootstrap ? (
                  <div className="context-card" role="status">
                    <div className="chip-row">
                      <span className="chip">
                        {t("planner.planningDate")}: {bootstrap.planning_date}
                      </span>
                      <span className="chip">
                        {bootstrap.candidates.length} {t("planner.catalogReady")}
                      </span>
                    </div>
                    {bootstrap.daily_nutrition_state ? (
                      <div className="context-state">
                        <strong>{t("planner.stateReady")}</strong>
                        <div className="chip-row">
                          <span className="chip">
                            {t("planner.energyConsumed")}: {formatNumber(
                              bootstrap.daily_nutrition_state.energy_consumed_kcal,
                              locale,
                              0,
                            )} {t("results.kcal")}
                          </span>
                          <span className="chip">
                            {t("planner.energyPlanned")}: {formatNumber(
                              bootstrap.daily_nutrition_state.energy_planned_kcal,
                              locale,
                              0,
                            )} {t("results.kcal")}
                          </span>
                        </div>
                      </div>
                    ) : (
                      <p className="context-warning">{t("planner.stateMissing")}</p>
                    )}
                    {bootstrap.candidates.length === 0 ? (
                      <p className="context-warning">{t("planner.catalogEmpty")}</p>
                    ) : null}
                  </div>
                ) : null}

                <div className="form-grid three">
                  <label className="field">
                    <span>{t("planner.availableMinutes")}</span>
                    <input
                      min="0"
                      step="1"
                      type="number"
                      value={availableMinutes}
                      onChange={(event) => setAvailableMinutes(event.target.value)}
                    />
                  </label>
                  <label className="field">
                    <span>{t("planner.kitchen")}</span>
                    <select
                      value={kitchen}
                      onChange={(event) => setKitchen(event.target.value as KitchenState)}
                    >
                      <option value="unknown">{t("planner.unknown")}</option>
                      <option value="yes">{t("planner.yes")}</option>
                      <option value="no">{t("planner.no")}</option>
                    </select>
                  </label>
                </div>

                <div className="field-group">
                  <span className="field-group__label">{t("planner.sources")}</span>
                  <div className="source-grid">
                    {SOURCE_KINDS.map((source) => (
                      <label className="source-toggle" key={source}>
                        <input
                          checked={sourceKinds.includes(source)}
                          onChange={() => toggleSource(source)}
                          type="checkbox"
                        />
                        <span>{t(`source.${source}`)}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="candidate-section">
                  <div className="candidate-section__header">
                    <span className="field-group__label">{t("planner.candidates")}</span>
                    <button
                      className="text-button"
                      disabled={
                        !bootstrap ||
                        bootstrap.candidates.length === 0 ||
                        candidates.length >= bootstrap.candidates.length
                      }
                      onClick={() => setCandidates((current) => [...current, newCandidateDraft()])}
                      type="button"
                    >
                      + {t("planner.addCandidate")}
                    </button>
                  </div>

                  <div className="candidate-list">
                    {candidates.map((candidate, index) => (
                      <div className="candidate-row" key={candidate.rowId}>
                        <span className="candidate-index">{String(index + 1).padStart(2, "0")}</span>
                        <label className="field candidate-composition">
                          <span>{t("planner.candidate")}</span>
                          <select
                            value={candidate.composition_id}
                            onChange={(event) =>
                              selectCandidate(candidate.rowId, event.target.value)
                            }
                          >
                            <option value="">{t("planner.chooseCandidate")}</option>
                            {bootstrap?.candidates.map((option) => (
                              <option
                                disabled={candidates.some(
                                  (row) =>
                                    row.rowId !== candidate.rowId &&
                                    row.composition_id === option.composition_id,
                                )}
                                key={option.composition_id}
                                value={option.composition_id}
                              >
                                {candidateLabel(option, locale)}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="field narrow-field">
                          <span>{t("planner.quantity")}</span>
                          <input
                            min="0.0001"
                            step="any"
                            type="number"
                            value={candidate.quantity}
                            onChange={(event) =>
                              updateCandidate(candidate.rowId, { quantity: event.target.value })
                            }
                          />
                        </label>
                        <label className="field narrow-field">
                          <span>{t("planner.unit")}</span>
                          <input
                            value={candidate.quantity_unit}
                            onChange={(event) =>
                              updateCandidate(candidate.rowId, {
                                quantity_unit: event.target.value,
                              })
                            }
                          />
                        </label>
                        <button
                          aria-label={t("planner.remove")}
                          className="icon-button"
                          disabled={candidates.length === 1}
                          onClick={() =>
                            setCandidates((current) =>
                              current.filter((item) => item.rowId !== candidate.rowId),
                            )
                          }
                          type="button"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                <button
                  className="button primary large"
                  disabled={
                    busy?.kind === "recommendation" ||
                    bootstrapBusy ||
                    !bootstrap?.daily_nutrition_state ||
                    candidates.length === 0
                  }
                  type="submit"
                >
                  {busy?.kind === "recommendation"
                    ? t("status.loadingRecommendation")
                    : t("planner.recommend")}
                </button>
              </fieldset>
            </form>
          </section>
        </div>

        <section className="results-section">
          <div className="section-heading horizontal">
            <div>
              <span className="section-number">03</span>
              <h2>{t("results.title")}</h2>
            </div>
            {recommendation ? (
              <span className="run-id">
                {t("results.run")}: {recommendation.id.slice(0, 8)}
              </span>
            ) : null}
          </div>

          {recommendation ? (
            <div className="recommendation-grid">
              {recommendation.options.map((option) => (
                <RecommendationCard
                  decision={decisions[option.id]}
                  decisionBusy={busy?.kind === "decision" && busy.optionId === option.id}
                  key={option.id}
                  onDecision={handleDecision}
                  option={option}
                  recommendation={recommendation}
                />
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <span className="empty-orbit" aria-hidden="true" />
              <p>{t("empty.results")}</p>
            </div>
          )}
        </section>
      </main>

      <footer className="footer">
        <span>{t("footer.devNote")}</span>
      </footer>
    </div>
  );
}
