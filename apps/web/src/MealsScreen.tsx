import type { FamilyDashboard } from "./api/types";
import { memberDisplayName, formatMealTime } from "./FamilyHome";
import { useI18n } from "./i18n";
import MealPlanner from "./MealPlanner";

export type MealsView = "today" | "week" | "recommend";

const COPY = {
  "pt-PT": {
    title: "Refeições",
    help: "Hoje, semana e recomendações em ecrãs separados e leves.",
    navigation: "Navegação de refeições",
    today: "Hoje",
    week: "Semana",
    recommend: "Recomendar",
    todayTitle: "Refeições de hoje",
    weekTitle: "Plano semanal",
    weekHelp:
      "A vista semanal será ligada a uma leitura por intervalo do backend no próximo incremento, sem fazer sete pedidos separados no browser.",
  },
  en: {
    title: "Meals",
    help: "Today, week and recommendations in separate lightweight screens.",
    navigation: "Meals navigation",
    today: "Today",
    week: "Week",
    recommend: "Recommend",
    todayTitle: "Today's meals",
    weekTitle: "Weekly plan",
    weekHelp:
      "The weekly view will use a backend range read model in the next increment rather than issuing seven separate browser requests.",
  },
} as const;

export function mealParticipantNames(
  dashboard: FamilyDashboard,
  participantIds: string[],
): string {
  return participantIds
    .map((personId) => dashboard.members.find((member) => member.person_id === personId))
    .filter((member) => member !== undefined)
    .map(memberDisplayName)
    .join(" · ");
}

export default function MealsScreen({
  dashboard,
  familyId,
  view,
  onViewChange,
}: {
  dashboard: FamilyDashboard;
  familyId: string;
  view: MealsView;
  onViewChange: (view: MealsView) => void;
}) {
  const { locale, t } = useI18n();
  const copy = COPY[locale];

  return (
    <div className="meals-screen">
      <header className="screen-header compact-screen-header">
        <div>
          <span className="eyebrow">{t("nav.meals")}</span>
          <h1>{copy.title}</h1>
          <p>{copy.help}</p>
        </div>
      </header>

      <nav className="meals-tabs" aria-label={copy.navigation}>
        <button
          aria-current={view === "today" ? "page" : undefined}
          className={view === "today" ? "active" : ""}
          onClick={() => onViewChange("today")}
          type="button"
        >
          {copy.today}
        </button>
        <button
          aria-current={view === "week" ? "page" : undefined}
          className={view === "week" ? "active" : ""}
          onClick={() => onViewChange("week")}
          type="button"
        >
          {copy.week}
        </button>
        <button
          aria-current={view === "recommend" ? "page" : undefined}
          className={view === "recommend" ? "active" : ""}
          onClick={() => onViewChange("recommend")}
          type="button"
        >
          {copy.recommend}
        </button>
      </nav>

      {view === "today" ? (
        <section className="meals-panel" aria-labelledby="meals-today-heading">
          <div className="meals-panel__heading">
            <div>
              <h2 id="meals-today-heading">{copy.todayTitle}</h2>
              <p>{dashboard.dashboard_date}</p>
            </div>
            <button className="button primary" onClick={() => onViewChange("recommend")} type="button">
              {copy.recommend}
            </button>
          </div>

          {dashboard.meals.length > 0 ? (
            <div className="meal-agenda meals-agenda--standalone">
              {dashboard.meals.map((meal) => {
                const names = mealParticipantNames(dashboard, meal.participant_person_ids);
                return (
                  <article className="agenda-row" key={meal.id}>
                    <time>{formatMealTime(meal.scheduled_at, dashboard.timezone, locale)}</time>
                    <div className="agenda-row__body">
                      <strong>{meal.title ?? meal.meal_type}</strong>
                      <span>
                        {names || t("home.familyMeal")}
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
              <button className="button secondary" onClick={() => onViewChange("recommend")} type="button">
                {copy.recommend}
              </button>
            </div>
          )}
        </section>
      ) : null}

      {view === "week" ? (
        <section className="meals-panel meals-week-placeholder" aria-labelledby="meals-week-heading">
          <span className="eyebrow">{copy.week}</span>
          <h2 id="meals-week-heading">{copy.weekTitle}</h2>
          <p>{copy.weekHelp}</p>
        </section>
      ) : null}

      {view === "recommend" ? <MealPlanner familyId={familyId} /> : null}
    </div>
  );
}
