import { useEffect, useMemo, useState } from "react";

import { getPerson, getPersonEnergyProfile, getPersonPlanningContext } from "./api/setupClient";
import type { PersonEnergyProfile } from "./api/setupTypes";
import type {
  FamilyDashboard,
  FamilyDashboardMeal,
  FamilyDashboardMember,
  Person,
  PlanningDailyNutritionState,
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
    planned: "Planeadas",
    assumed: "Assumidas",
    remaining: "Energia restante",
    target: "Meta diária",
    bmr: "Metabolismo basal",
    tdee: "Gasto diário estimado",
    steps: "Passos",
    activeEnergy: "Energia ativa",
    usualActivity: "Atividade habitual",
    weight: "Peso",
    height: "Altura",
    weightTrend: "Tendência 7 dias",
    sleep: "Sono",
    restingHeartRate: "FC repouso",
    meals: "Refeições de hoje",
    mealsHelp: "Apenas as refeições em que esta pessoa participa.",
    noMeals: "Sem refeições para esta pessoa hoje.",
    noData: "Sem dados",
    kcal: "kcal",
    breakfast: "Pequeno-almoço padrão",
    goal: "Objetivo",
    birthDate: "Data de nascimento",
    sex: "Sexo para cálculo energético",
    timezone: "Fuso horário",
    male: "Masculino",
    female: "Feminino",
    sedentary: "Sedentário",
    light: "Ligeira",
    moderate: "Moderada",
    active: "Ativo",
    very_active: "Muito ativo",
    maintain: "Manter peso",
    lose: "Perder peso",
    gain: "Ganhar peso",
    perWeek: "kg/semana",
    nutritionHelp: "Objetivos energéticos e estado do dia usados pelo recomendador.",
    activityHelp:
      "O nível habitual usado no cálculo energético aparece já; medições de atividade entram quando houver uma fonte ligada.",
    profileHelp: "Dados de base usados para calcular necessidades energéticas e personalizar o planeamento.",
    placeholderHealth:
      "Aqui ficará a evidência de saúde e bem-estar proveniente das fontes ligadas, sem interpretação clínica automática.",
    placeholderHistory:
      "Aqui ficará a linha temporal de peso, atividade, nutrição e refeições.",
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
    planned: "Planned",
    assumed: "Assumed",
    remaining: "Energy remaining",
    target: "Daily target",
    bmr: "Basal metabolism",
    tdee: "Estimated daily expenditure",
    steps: "Steps",
    activeEnergy: "Active energy",
    usualActivity: "Usual activity",
    weight: "Weight",
    height: "Height",
    weightTrend: "7-day trend",
    sleep: "Sleep",
    restingHeartRate: "Resting HR",
    meals: "Today's meals",
    mealsHelp: "Only meals this person participates in.",
    noMeals: "No meals for this person today.",
    noData: "No data",
    kcal: "kcal",
    breakfast: "Standard breakfast",
    goal: "Goal",
    birthDate: "Date of birth",
    sex: "Sex for energy calculation",
    timezone: "Timezone",
    male: "Male",
    female: "Female",
    sedentary: "Sedentary",
    light: "Light",
    moderate: "Moderate",
    active: "Active",
    very_active: "Very active",
    maintain: "Maintain weight",
    lose: "Lose weight",
    gain: "Gain weight",
    perWeek: "kg/week",
    nutritionHelp: "Energy targets and today's state used by the recommendation engine.",
    activityHelp:
      "The usual activity level used for energy calculations is available now; measured activity appears when a source is connected.",
    profileHelp: "Base data used to calculate energy needs and personalize planning.",
    placeholderHealth:
      "This screen will show connected-source health and wellness evidence without automatic clinical interpretation.",
    placeholderHistory:
      "This screen will show the timeline of weight, activity, nutrition and meals.",
    comingNext: "Dedicated screen",
  },
} as const;

export function personMeals(
  dashboard: FamilyDashboard,
  personId: string,
): FamilyDashboardMeal[] {
  return dashboard.meals.filter((meal) => meal.participant_person_ids.includes(personId));
}

function formatNumber(value: string | number, locale: Locale, digits = 0): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  return new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(numeric);
}

function kcal(value: string | number | null | undefined, locale: Locale): string | null {
  if (value === null || value === undefined) return null;
  return `${formatNumber(value, locale)} kcal`;
}

function energyRange(
  minimum: string | null | undefined,
  maximum: string | null | undefined,
  locale: Locale,
): string | null {
  if (minimum === null || minimum === undefined) {
    return maximum === null || maximum === undefined ? null : kcal(maximum, locale);
  }
  if (maximum === null || maximum === undefined) return kcal(minimum, locale);
  return `${formatNumber(minimum, locale)}–${formatNumber(maximum, locale)} kcal`;
}

function formatMealTime(scheduledAt: string, timezone: string, locale: Locale): string {
  return new Intl.DateTimeFormat(locale, {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  }).format(new Date(scheduledAt));
}

function formatDate(value: string | null, locale: Locale): string | null {
  if (!value) return null;
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: "UTC" }).format(
    new Date(`${value}T00:00:00Z`),
  );
}

function formatSleep(minutes: number | null, locale: Locale): string | null {
  if (minutes === null) return null;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return locale === "pt-PT" ? `${hours} h ${rest} min` : `${hours}h ${rest}m`;
}

function signedTrend(value: string | null, locale: Locale): string | null {
  if (value === null) return null;
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return value;
  const formatted = new Intl.NumberFormat(locale, {
    maximumFractionDigits: 1,
    signDisplay: "always",
  }).format(numeric);
  return `${formatted} kg`;
}

function sectionLabel(section: PersonSection, locale: Locale): string {
  return COPY[locale][section];
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="person-detail-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PlaceholderSection({ section, locale }: { section: "health" | "history"; locale: Locale }) {
  const copy = COPY[locale];
  return (
    <section className="person-placeholder">
      <span className="eyebrow">{copy.comingNext}</span>
      <h2>{sectionLabel(section, locale)}</h2>
      <p>{section === "health" ? copy.placeholderHealth : copy.placeholderHistory}</p>
    </section>
  );
}

function goalText(profile: PersonEnergyProfile, locale: Locale): string {
  const copy = COPY[locale];
  const base = copy[profile.goal_type];
  if (profile.target_rate_kg_per_week === null) return base;
  return `${base} · ${formatNumber(profile.target_rate_kg_per_week, locale, 1)} ${copy.perWeek}`;
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
  const [person, setPerson] = useState<Person | null>(null);
  const [profile, setProfile] = useState<PersonEnergyProfile | null>(null);
  const [dailyState, setDailyState] = useState<PlanningDailyNutritionState | null>(null);
  const meals = useMemo(
    () => personMeals(dashboard, member.person_id),
    [dashboard, member.person_id],
  );

  useEffect(() => {
    let cancelled = false;
    const now = new Date().toISOString();
    void Promise.all([
      getPerson(member.person_id).catch(() => null),
      getPersonEnergyProfile(member.person_id).catch(() => null),
      getPersonPlanningContext(member.person_id, now).catch(() => null),
    ]).then(([personResult, profileResult, contextResult]) => {
      if (cancelled) return;
      setPerson(personResult);
      setProfile(profileResult);
      setDailyState(contextResult?.daily_nutrition_state ?? null);
    });
    return () => {
      cancelled = true;
    };
  }, [member.person_id]);

  const consumed = dailyState?.energy_consumed_kcal ?? member.nutrition?.energy_consumed_kcal;
  const planned = dailyState?.energy_planned_kcal ?? member.nutrition?.energy_planned_kcal;
  const assumed = dailyState?.energy_assumed_kcal ?? "0";
  const remainingMin =
    dailyState?.energy_remaining_min_kcal ?? member.nutrition?.energy_remaining_min_kcal;
  const remainingMax =
    dailyState?.energy_remaining_max_kcal ?? member.nutrition?.energy_remaining_max_kcal;
  const remaining = energyRange(remainingMin, remainingMax, locale);
  const sleep = member.health ? formatSleep(member.health.sleep_duration_minutes, locale) : null;
  const trend = member.health ? signedTrend(member.health.weight_trend_7d_kg, locale) : null;
  const weight = profile?.weight_kg ?? member.health?.latest_weight_kg ?? null;

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
                <strong>{kcal(consumed, locale) ?? copy.noData}</strong>
                <small>{remaining ? `${copy.remaining}: ${remaining}` : copy.noData}</small>
              </article>

              <article className="person-metric-card">
                <span>{copy.steps}</span>
                <strong>
                  {member.health?.steps !== null && member.health?.steps !== undefined
                    ? formatNumber(member.health.steps, locale)
                    : copy.noData}
                </strong>
                <small>
                  {profile
                    ? `${copy.usualActivity}: ${copy[profile.activity_level]}`
                    : member.health?.active_energy_kcal
                      ? `${copy.activeEnergy}: ${formatNumber(member.health.active_energy_kcal, locale)} ${copy.kcal}`
                      : copy.noData}
                </small>
              </article>

              <article className="person-metric-card">
                <span>{copy.weight}</span>
                <strong>{weight ? `${formatNumber(weight, locale, 1)} kg` : copy.noData}</strong>
                <small>{trend ? `${copy.weightTrend}: ${trend}` : profile ? copy.goal + ": " + goalText(profile, locale) : copy.noData}</small>
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
                      <strong>{meal.title ?? meal.meal_type}</strong>
                      <span>{meal.location ?? meal.meal_type}</span>
                    </div>
                    <span>{meal.status}</span>
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
      ) : null}

      {section === "nutrition" ? (
        <section className="person-section">
          <div className="home-section__heading">
            <div>
              <h2>{copy.nutrition}</h2>
              <p>{copy.nutritionHelp}</p>
            </div>
          </div>
          <div className="person-detail-grid">
            <DetailItem
              label={copy.target}
              value={profile ? energyRange(profile.energy_min_kcal, profile.energy_max_kcal, locale) ?? copy.noData : copy.noData}
            />
            <DetailItem label={copy.consumed} value={kcal(consumed, locale) ?? copy.noData} />
            <DetailItem label={copy.planned} value={kcal(planned, locale) ?? copy.noData} />
            <DetailItem label={copy.assumed} value={kcal(assumed, locale) ?? copy.noData} />
            <DetailItem label={copy.remaining} value={remaining ?? copy.noData} />
            <DetailItem label={copy.tdee} value={profile ? kcal(profile.estimated_tdee_kcal, locale) ?? copy.noData : copy.noData} />
            <DetailItem label={copy.bmr} value={profile ? kcal(profile.estimated_bmr_kcal, locale) ?? copy.noData : copy.noData} />
            <DetailItem label={copy.breakfast} value={profile ? kcal(profile.standard_breakfast_kcal, locale) ?? copy.noData : copy.noData} />
            <DetailItem label={copy.goal} value={profile ? goalText(profile, locale) : copy.noData} />
          </div>
        </section>
      ) : null}

      {section === "activity" ? (
        <section className="person-section">
          <div className="home-section__heading">
            <div>
              <h2>{copy.activity}</h2>
              <p>{copy.activityHelp}</p>
            </div>
          </div>
          <div className="person-detail-grid">
            <DetailItem
              label={copy.usualActivity}
              value={profile ? copy[profile.activity_level] : copy.noData}
            />
            <DetailItem
              label={copy.tdee}
              value={profile ? kcal(profile.estimated_tdee_kcal, locale) ?? copy.noData : copy.noData}
            />
            <DetailItem
              label={copy.steps}
              value={member.health?.steps !== null && member.health?.steps !== undefined ? formatNumber(member.health.steps, locale) : copy.noData}
            />
            <DetailItem
              label={copy.activeEnergy}
              value={member.health?.active_energy_kcal ? kcal(member.health.active_energy_kcal, locale) ?? copy.noData : copy.noData}
            />
          </div>
        </section>
      ) : null}

      {section === "profile" ? (
        <section className="person-section">
          <div className="home-section__heading">
            <div>
              <h2>{copy.profile}</h2>
              <p>{copy.profileHelp}</p>
            </div>
          </div>
          <div className="person-detail-grid">
            <DetailItem label={copy.birthDate} value={formatDate(person?.birth_date ?? null, locale) ?? copy.noData} />
            <DetailItem label={copy.sex} value={profile ? copy[profile.sex_for_energy_calculation] : copy.noData} />
            <DetailItem label={copy.height} value={profile ? `${formatNumber(profile.height_cm, locale, 1)} cm` : copy.noData} />
            <DetailItem label={copy.weight} value={profile ? `${formatNumber(profile.weight_kg, locale, 1)} kg` : copy.noData} />
            <DetailItem label={copy.usualActivity} value={profile ? copy[profile.activity_level] : copy.noData} />
            <DetailItem label={copy.goal} value={profile ? goalText(profile, locale) : copy.noData} />
            <DetailItem label={copy.timezone} value={person?.timezone ?? member.timezone} />
            <DetailItem label={copy.breakfast} value={profile ? kcal(profile.standard_breakfast_kcal, locale) ?? copy.noData : copy.noData} />
          </div>
        </section>
      ) : null}

      {section === "health" || section === "history" ? (
        <PlaceholderSection locale={locale} section={section} />
      ) : null}
    </div>
  );
}
