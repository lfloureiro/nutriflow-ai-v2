import { useEffect, useMemo, useState } from "react";

import { ApiError, getFamilyMeals } from "./api/client";
import type { FamilyMeal, FamilyMeals, FamilyMealsDay } from "./api/types";
import FamilyMealDetailScreen from "./FamilyMealDetail";
import { useI18n, type Locale } from "./i18n";
import MealPlanner from "./MealPlanner";

export type FamilyMealsMode = "today" | "week" | "recommend";

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.message} (HTTP ${error.status})`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

export function startOfWeekDate(isoDate: string): string {
  const value = new Date(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(value.getTime())) {
    throw new Error("Invalid ISO calendar date.");
  }
  const weekday = value.getUTCDay();
  const offset = weekday === 0 ? -6 : 1 - weekday;
  value.setUTCDate(value.getUTCDate() + offset);
  return value.toISOString().slice(0, 10);
}

export function familyMealParticipantNames(meal: FamilyMeal): string {
  return meal.participants
    .map((participant) =>
      [participant.first_name, participant.last_name].filter(Boolean).join(" "),
    )
    .join(" · ");
}

function formatDate(value: string, locale: Locale, includeWeekday = true): string {
  return new Intl.DateTimeFormat(locale, {
    weekday: includeWeekday ? "long" : undefined,
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function formatTime(value: string, timezone: string, locale: Locale): string {
  return new Intl.DateTimeFormat(locale, {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  }).format(new Date(value));
}

function MealRow({
  meal,
  familyTimezone,
  onOpenMeal,
}: {
  meal: FamilyMeal;
  familyTimezone: string;
  onOpenMeal: (mealId: string) => void;
}) {
  const { locale, t } = useI18n();
  const participantNames = familyMealParticipantNames(meal);

  function statusLabel(): string {
    switch (meal.status) {
      case "planned":
        return t("meals.statusPlanned");
      case "prepared":
        return t("meals.statusPrepared");
      case "served":
        return t("meals.statusServed");
      case "completed":
        return t("meals.statusCompleted");
      default:
        return meal.status;
    }
  }

  function mealTypeLabel(): string {
    switch (meal.meal_type) {
      case "breakfast":
        return t("meals.breakfast");
      case "lunch":
        return t("meals.lunch");
      case "dinner":
        return t("meals.dinner");
      case "snack":
        return t("meals.snack");
      default:
        return meal.meal_type;
    }
  }

  const title = meal.title ?? mealTypeLabel();

  return (
    <button
      aria-label={`${t("mealDetail.open")}: ${title}`}
      className="family-meal-row"
      onClick={() => onOpenMeal(meal.id)}
      type="button"
    >
      <time>{formatTime(meal.scheduled_at, familyTimezone, locale)}</time>
      <span className="family-meal-row__body">
        <strong>{title}</strong>
        <span>
          {participantNames || t("home.familyMeal")}
          {meal.location ? ` · ${meal.location}` : ""}
        </span>
      </span>
      <span className={`family-meal-status status-${meal.status}`}>{statusLabel()}</span>
    </button>
  );
}

function DaySection({
  day,
  timezone,
  onOpenMeal,
  compact = false,
}: {
  day: FamilyMealsDay;
  timezone: string;
  onOpenMeal: (mealId: string) => void;
  compact?: boolean;
}) {
  const { locale, t } = useI18n();

  return (
    <section className={`family-meals-day ${compact ? "compact" : ""}`}>
      <div className="family-meals-day__heading">
        <h2>{formatDate(day.date, locale)}</h2>
        <span>
          {day.meals.length === 1
            ? t("meals.oneMeal")
            : `${day.meals.length} ${t("meals.mealCount")}`}
        </span>
      </div>
      {day.meals.length > 0 ? (
        <div className="family-meals-list">
          {day.meals.map((meal) => (
            <MealRow
              familyTimezone={timezone}
              key={meal.id}
              meal={meal}
              onOpenMeal={onOpenMeal}
            />
          ))}
        </div>
      ) : (
        <div className="family-meals-empty-day">{t("meals.noMealsDay")}</div>
      )}
    </section>
  );
}

export default function FamilyMealsScreen({
  familyId,
  referenceDate,
  mode,
  onModeChange,
}: {
  familyId: string;
  referenceDate?: string;
  mode: FamilyMealsMode;
  onModeChange: (mode: FamilyMealsMode) => void;
}) {
  const { locale, t } = useI18n();
  const [data, setData] = useState<FamilyMeals | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedMealId, setSelectedMealId] = useState<string | null>(null);

  const request = useMemo(() => {
    if (mode === "recommend") {
      return null;
    }
    if (mode === "today") {
      return { startDate: referenceDate, days: 1 };
    }
    return {
      startDate: referenceDate ? startOfWeekDate(referenceDate) : undefined,
      days: 7,
    };
  }, [mode, referenceDate]);

  useEffect(() => {
    if (request === null) {
      return;
    }

    let cancelled = false;
    setBusy(true);
    setError(null);
    void getFamilyMeals(familyId, request.startDate, request.days)
      .then((result) => {
        if (!cancelled) {
          setData(result);
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setData(null);
          setError(errorText(caught));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setBusy(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [familyId, request]);

  if (selectedMealId !== null) {
    return (
      <FamilyMealDetailScreen
        familyId={familyId}
        mealEventId={selectedMealId}
        onBack={() => setSelectedMealId(null)}
      />
    );
  }

  function changeMode(nextMode: FamilyMealsMode) {
    setSelectedMealId(null);
    onModeChange(nextMode);
  }

  return (
    <div className="family-meals-screen">
      <header className="screen-header compact-screen-header family-meals-header">
        <div>
          <span className="eyebrow">{t("nav.meals")}</span>
          <h1>{t("meals.title")}</h1>
          <p>{t("meals.help")}</p>
        </div>
        <button
          className="button primary"
          onClick={() => changeMode("recommend")}
          type="button"
        >
          {t("meals.recommend")}
        </button>
      </header>

      <nav className="secondary-tabs family-meals-tabs" aria-label={t("meals.navigation")}>
        <button
          aria-current={mode === "today" ? "page" : undefined}
          className={mode === "today" ? "active" : ""}
          onClick={() => changeMode("today")}
          type="button"
        >
          {t("meals.today")}
        </button>
        <button
          aria-current={mode === "week" ? "page" : undefined}
          className={mode === "week" ? "active" : ""}
          onClick={() => changeMode("week")}
          type="button"
        >
          {t("meals.week")}
        </button>
        <button
          aria-current={mode === "recommend" ? "page" : undefined}
          className={mode === "recommend" ? "active" : ""}
          onClick={() => changeMode("recommend")}
          type="button"
        >
          {t("meals.recommendShort")}
        </button>
      </nav>

      {mode === "recommend" ? <MealPlanner familyId={familyId} /> : null}

      {mode !== "recommend" && error ? (
        <div className="error-banner" role="alert">
          <strong>{t("error.title")}</strong>
          <span>{error}</span>
        </div>
      ) : null}

      {mode !== "recommend" && busy ? (
        <div className="shell-loading" role="status">
          {t("meals.loading")}
        </div>
      ) : null}

      {mode !== "recommend" && !busy && !error && data ? (
        <div className="family-meals-content">
          {mode === "week" ? (
            <div className="family-meals-range">
              <span>{t("meals.weekRange")}</span>
              <strong>
                {formatDate(data.start_date, locale, false)} —{" "}
                {formatDate(data.end_date, locale, false)}
              </strong>
            </div>
          ) : null}
          {data.days.map((day) => (
            <DaySection
              compact={mode === "week"}
              day={day}
              key={day.date}
              onOpenMeal={setSelectedMealId}
              timezone={data.timezone}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
