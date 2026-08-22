import { useMemo, useState } from "react";

import type {
  FamilyDashboard,
  FamilyDashboardMeal,
  FamilyDashboardMember,
} from "./api/types";
import { memberDisplayName } from "./FamilyHome";
import type { Locale } from "./i18n";
import { useI18n } from "./i18n";

type PersonSection =
  | "overview"
  | "nutrition"
  | "activity"
  | "health"
  | "history"
  | "profile";

const SECTION_ORDER: PersonSection[] = [
  "overview",
  "nutrition",
  "activity",
  "health",
  "history",
  "profile",
];

const COPY = {
  "pt-PT": {
    back: "Pessoas",
    overview: "Visão geral",
    nutrition: "Nutrição",
    activity: "Atividade",
    health: "Saúde",
    history: "Histórico",
    profile: "Perfil",
    today: "Hoje",
    todayHelp: "O essencial desta pessoa para o dia atual.",
    consumed: "Energia consumida",
    remaining: "Energia restante",
    steps: "Passos",
    activeEnergy: "Energia ativa",
    weight: "Peso",
    weightTrend: "Tendência 7 dias",
    sleep: "Sono",
    restingHeartRate: "FC repouso",
    meals: "Refeições de hoje",
    mealsHelp: "Apenas as refeições em que esta pessoa participa.",
    noMeals: "Sem refeições para esta pessoa hoje.",
    noData: "Sem dados",
    kcal: "kcal",
    placeholderNutrition:
      "Aqui ficará a comparação detalhada entre consumo, planeamento e objetivos nutricionais.",
    placeholderActivity:
      "Aqui ficará o detalhe de movimento, energia ativa e histórico de atividade.",
    placeholderHealth:
      "Aqui ficará a evidência de saúde e bem-estar proveniente das fontes ligadas, sem interpretação clínica automática.",
    placeholderHistory:
      "Aqui ficará a linha temporal de peso, atividade, nutrição e refeições.",
    placeholderProfile:
      "Aqui ficarão objetivos, restrições, preferências e integrações desta pessoa.",
    comingNext: "Ecrã dedicado",
  },
  en: {
    back: "People",
    overview: "Overview",
    nutrition: "Nutrition",
    activity: "Activity",
    health: "Health",
    history: "History",
    profile: "Profile",
    today: "Today",
    todayHelp: "The essentials for this person today.",
    consumed: "Energy consumed",
    remaining: "Energy remaining",
    steps: "Steps",
    activeEnergy: "Active energy",
    weight: "Weight",
    weightTrend: "7-day trend",
    sleep: "Sleep",
    restingHeartRate: "Resting HR",
    meals: "Today's meals",
    mealsHelp: "Only meals this person participates in.",
    noMeals: "No meals for this person today.",
    noData: "No data",
    kcal: "kcal",
    placeholderNutrition:
      "This screen will show detailed intake, planning and nutrition-target comparisons.",
    placeholderActivity:
      "This screen will show movement, active energy and activity history.",
    placeholderHealth:
      "This screen will show connected-source health and wellness evidence without automatic clinical interpretation.",
    placeholderHistory:
      "This screen will show the timeline of weight, activity, nutrition and meals.",
    placeholderProfile:
      "This screen will hold goals, constraints, preferences and integrations for this person.",
    comingNext: "Dedicated screen",
  },
} as const;

const MEAL_TYPE_LABELS: Record<Locale, Record<string, string>> = {
  "pt-PT": {
    breakfast: "Pequeno-almoço",
    lunch: "Almoço",
    dinner: "Jantar",
    snack: "Lanche",
  },
  en: {
    breakfast: "Breakfast",
    lunch: "Lunch",
    dinner: "Dinner",
    snack: "Snack",
  },
};

const MEAL_STATUS_LABELS: Record<Locale, Record<string, string>> = {
  "pt-PT": {
    planned: "Planeada",
    prepared: "Preparada",
    served: "Servida",
    completed: "Concluída",
    cancelled: "Cancelada",
    replaced: "Substituída",
  },
  en: {
    planned: "Planned",
    prepared: "Prepared",
    served: "Served",
    completed: "Completed",
    cancelled: "Cancelled",
    replaced: "Replaced",
  },
};

export function personMeals(
  dashboard: FamilyDashboard,
  personId: string,
): FamilyDashboardMeal[] {
  return dashboard.meals.filter((meal) => meal.participant_person_ids.includes(personId));
}

export function mealTypeLabel(mealType: string, locale: Locale): string {
  return MEAL_TYPE_LABELS[locale][mealType] ?? mealType;
}

export function mealStatusLabel(status: string, locale: Locale): string {
  return MEAL_STATUS_LABELS[locale][status] ?? status;
}

function formatNumber(value: string | number, locale: Locale, digits = 0): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return String(value);
  }
  return new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(numeric);
}

function formatMealTime(scheduledAt: string, timezone: string, locale: Locale): string {
  return new Intl.DateTimeFormat(locale, {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  }).format(new Date(scheduledAt));
}

function formatSleep(minutes: number | null, locale: Locale): string | null {
  if (minutes === null) {
    return null;
  }
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return locale === "pt-PT" ? `${hours} h ${rest} min` : `${hours}h ${rest}m`;
}

function signedTrend(value: string | null, locale: Locale): string | null {
  if (value === null) {
    return null;
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return value;
  }
  const formatted = new Intl.NumberFormat(locale, {
    maximumFractionDigits: 1,
    signDisplay: "always",
  }).format(numeric);
  return `${formatted} kg`;
}

function sectionLabel(section: PersonSection, locale: Locale): string {
  return COPY[locale][section];
}

function PlaceholderSection({ section, locale }: { section: PersonSection; locale: Locale }) {
  const copy = COPY[locale];
  const text =
    section === "nutrition"
      ? copy.placeholderNutrition
      : section === "activity"
        ? copy.placeholderActivity
        : section === "health"
          ? copy.placeholderHealth
          : section === "history"
            ? copy.placeholderHistory
            : copy.placeholderProfile;

  return (
    <section className="person-placeholder">
      <span className="eyebrow">{copy.comingNext}</span>
      <h2>{sectionLabel(section, locale)}</h2>
      <p>{text}</p>
    </section>
  );
}

export default function PersonOverview({
  dashboard,
  member,
  onBack,
}: {
  dashboard: FamilyDashboard;
  member: FamilyDashboardMember;
  onBack: () => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [section, setSection] = useState<PersonSection>("overview");
  const meals = useMemo(
    () => personMeals(dashboard, member.person_id),
    [dashboard, member.person_id],
  );

  const remaining = member.nutrition
    ? [member.nutrition.energy_remaining_min_kcal, member.nutrition.energy_remaining_max_kcal]
        .filter((value): value is string => value !== null)
        .map((value) => formatNumber(value, locale))
        .join("–")
    : "";

  const sleep = member.health ? formatSleep(member.health.sleep_duration_minutes, locale) : null;
  const trend = member.health ? signedTrend(member.health.weight_trend_7d_kg, locale) : null;

  return (
    <div className="person-overview-screen">
      <header className="person-header">
        <button className="person-back" onClick={onBack} type="button">
          <span aria-hidden="true">‹</span>
          {copy.back}
        </button>
        <div className="person-header__identity">
          <span className="member-avatar person-header__avatar" aria-hidden="true">
            {member.first_name.slice(0, 1).toUpperCase()}
          </span>
          <div>
            <span className="eyebrow">{dashboard.dashboard_date}</span>
            <h1>{memberDisplayName(member)}</h1>
            <p>{member.timezone}</p>
          </div>
        </div>
      </header>

      <nav className="person-secondary-nav" aria-label={memberDisplayName(member)}>
        {SECTION_ORDER.map((item) => (
          <button
            aria-current={section === item ? "page" : undefined}
            className={section === item ? "active" : ""}
            key={item}
            onClick={() => setSection(item)}
            type="button"
          >
            {sectionLabel(item, locale)}
          </button>
        ))}
      </nav>

      {section === "overview" ? (
        <div className="person-overview-content">
          <section className="person-section" aria-labelledby="person-today-heading">
            <div className="home-section__heading">
              <div>
                <h2 id="person-today-heading">{copy.today}</h2>
                <p>{copy.todayHelp}</p>
              </div>
            </div>

            <div className="person-metric-grid">
              <article className="person-metric-card">
                <span>{copy.consumed}</span>
                <strong>
                  {member.nutrition
                    ? `${formatNumber(member.nutrition.energy_consumed_kcal, locale)} ${copy.kcal}`
                    : copy.noData}
                </strong>
                <small>
                  {member.nutrition && remaining
                    ? `${copy.remaining}: ${remaining} ${copy.kcal}`
                    : copy.noData}
                </small>
              </article>

              <article className="person-metric-card">
                <span>{copy.steps}</span>
                <strong>
                  {member.health?.steps !== null && member.health?.steps !== undefined
                    ? formatNumber(member.health.steps, locale)
                    : copy.noData}
                </strong>
                <small>
                  {member.health?.active_energy_kcal
                    ? `${copy.activeEnergy}: ${formatNumber(member.health.active_energy_kcal, locale)} ${copy.kcal}`
                    : copy.noData}
                </small>
              </article>

              <article className="person-metric-card">
                <span>{copy.weight}</span>
                <strong>
                  {member.health?.latest_weight_kg
                    ? `${formatNumber(member.health.latest_weight_kg, locale, 1)} kg`
                    : copy.noData}
                </strong>
                <small>{trend ? `${copy.weightTrend}: ${trend}` : copy.noData}</small>
              </article>

              <article className="person-metric-card">
                <span>{copy.sleep}</span>
                <strong>{sleep ?? copy.noData}</strong>
                <small>
                  {member.health?.resting_heart_rate_bpm
                    ? `${copy.restingHeartRate}: ${formatNumber(member.health.resting_heart_rate_bpm, locale)} bpm`
                    : copy.noData}
                </small>
              </article>
            </div>
          </section>

          <section className="person-section" aria-labelledby="person-meals-heading">
            <div className="home-section__heading">
              <div>
                <h2 id="person-meals-heading">{copy.meals}</h2>
                <p>{copy.mealsHelp}</p>
              </div>
            </div>

            {meals.length > 0 ? (
              <div className="person-meal-list">
                {meals.map((meal) => (
                  <article className="person-meal-row" key={meal.id}>
                    <time>{formatMealTime(meal.scheduled_at, dashboard.timezone, locale)}</time>
                    <div>
                      <strong>{meal.title ?? mealTypeLabel(meal.meal_type, locale)}</strong>
                      <span>{meal.location ?? mealTypeLabel(meal.meal_type, locale)}</span>
                    </div>
                    <span>{mealStatusLabel(meal.status, locale)}</span>
                  </article>
                ))}
              </div>
            ) : (
              <div className="home-empty person-empty">
                <strong>{copy.noMeals}</strong>
              </div>
            )}
          </section>
        </div>
      ) : (
        <PlaceholderSection locale={locale} section={section} />
      )}
    </div>
  );
}
