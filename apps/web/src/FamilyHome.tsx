import type { FamilyDashboard, FamilyDashboardMember } from "./api/types";
import { useI18n, type Locale } from "./i18n";

export function memberDisplayName(member: FamilyDashboardMember): string {
  return [member.first_name, member.last_name].filter(Boolean).join(" ");
}

export function formatMealTime(
  scheduledAt: string,
  timezone: string,
  locale: Locale,
): string {
  return new Intl.DateTimeFormat(locale, {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  }).format(new Date(scheduledAt));
}

function formatNumber(value: string | number, locale: Locale, digits = 0): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return String(value);
  }
  return new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(numeric);
}

function trendMarker(value: string | null): string {
  if (value === null) {
    return "";
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric === 0) {
    return "→";
  }
  return numeric < 0 ? "↓" : "↑";
}

function sleepText(minutes: number | null, locale: Locale): string {
  if (minutes === null) {
    return "—";
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return locale === "pt-PT"
    ? `${hours} h ${remainingMinutes} min`
    : `${hours}h ${remainingMinutes}m`;
}

function memberNamesForMeal(
  dashboard: FamilyDashboard,
  participantIds: string[],
): string {
  const names = participantIds
    .map((id) => dashboard.members.find((member) => member.person_id === id))
    .filter((member): member is FamilyDashboardMember => member !== undefined)
    .map(memberDisplayName);
  return names.join(" · ");
}

export default function FamilyHome({
  dashboard,
  onPlanMeal,
  onOpenPerson,
}: {
  dashboard: FamilyDashboard;
  onPlanMeal: () => void;
  onOpenPerson: (personId: string) => void;
}) {
  const { locale, t } = useI18n();

  return (
    <div className="family-home">
      <header className="screen-header">
        <div>
          <span className="eyebrow">{t("home.eyebrow")}</span>
          <h1>{t("home.title")}</h1>
          <p>
            {dashboard.family_name} · {dashboard.dashboard_date}
          </p>
        </div>
        <button className="button primary" onClick={onPlanMeal} type="button">
          {t("home.planMeal")}
        </button>
      </header>

      <section className="home-section" aria-labelledby="family-members-heading">
        <div className="home-section__heading">
          <div>
            <h2 id="family-members-heading">{t("home.family")}</h2>
            <p>{t("home.familyHelp")}</p>
          </div>
        </div>

        <div className="member-grid">
          {dashboard.members.map((member) => (
            <button
              className="member-card"
              key={member.person_id}
              onClick={() => onOpenPerson(member.person_id)}
              type="button"
            >
              <div className="member-card__identity">
                <span className="member-avatar" aria-hidden="true">
                  {member.first_name.slice(0, 1).toUpperCase()}
                </span>
                <div>
                  <strong>{memberDisplayName(member)}</strong>
                  <span>{t("home.openPerson")}</span>
                </div>
              </div>

              <dl className="member-metrics">
                <div>
                  <dt>{t("home.nutrition")}</dt>
                  <dd>
                    {member.nutrition ? (
                      <>
                        {formatNumber(member.nutrition.energy_consumed_kcal, locale)} {t("results.kcal")}
                        <span className="metric-subtle">
                          {t("home.consumed")}
                        </span>
                      </>
                    ) : (
                      <span className="metric-missing">{t("home.noData")}</span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt>{t("home.activity")}</dt>
                  <dd>
                    {member.health?.steps !== null && member.health?.steps !== undefined ? (
                      <>
                        {formatNumber(member.health.steps, locale)}
                        <span className="metric-subtle">{t("home.steps")}</span>
                      </>
                    ) : (
                      <span className="metric-missing">{t("home.noData")}</span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt>{t("home.weight")}</dt>
                  <dd>
                    {member.health?.latest_weight_kg ? (
                      <>
                        {formatNumber(member.health.latest_weight_kg, locale, 1)} kg {trendMarker(member.health.weight_trend_7d_kg)}
                      </>
                    ) : (
                      <span className="metric-missing">{t("home.noData")}</span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt>{t("home.sleep")}</dt>
                  <dd>
                    {member.health ? (
                      sleepText(member.health.sleep_duration_minutes, locale)
                    ) : (
                      <span className="metric-missing">{t("home.noData")}</span>
                    )}
                  </dd>
                </div>
              </dl>
            </button>
          ))}
        </div>
      </section>

      <section className="home-section" aria-labelledby="today-heading">
        <div className="home-section__heading">
          <div>
            <h2 id="today-heading">{t("home.today")}</h2>
            <p>{t("home.todayHelp")}</p>
          </div>
          <button className="text-button" onClick={onPlanMeal} type="button">
            {t("home.seeMeals")}
          </button>
        </div>

        {dashboard.meals.length > 0 ? (
          <div className="meal-agenda">
            {dashboard.meals.map((meal) => {
              const participantNames = memberNamesForMeal(
                dashboard,
                meal.participant_person_ids,
              );
              return (
                <article className="agenda-row" key={meal.id}>
                  <time>{formatMealTime(meal.scheduled_at, dashboard.timezone, locale)}</time>
                  <div className="agenda-row__body">
                    <strong>{meal.title ?? meal.meal_type}</strong>
                    <span>
                      {participantNames || t("home.familyMeal")}
                      {meal.location ? ` · ${meal.location}` : ""}
                    </span>
                  </div>
                  <span className="agenda-status">{meal.status}</span>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="home-empty">
            <strong>{t("home.noMeals")}</strong>
            <span>{t("home.noMealsHelp")}</span>
            <button className="button secondary" onClick={onPlanMeal} type="button">
              {t("home.planMeal")}
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
