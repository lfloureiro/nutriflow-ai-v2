import { useEffect, useState } from "react";

import { ApiError, getFamilyMealDetail } from "./api/client";
import type {
  FamilyMealDetail,
  FamilyMealDetailParticipant,
  FamilyMealDetailServing,
} from "./api/familyMealDetailTypes";
import { useI18n, type Locale } from "./i18n";

export type ServingEvidenceStage = "consumed" | "served" | "planned";

export type ServingEvidence = {
  stage: ServingEvidenceStage;
  quantity: string | null;
  energyKcal: string | null;
};

export function currentServingEvidence(serving: FamilyMealDetailServing): ServingEvidence | null {
  if (serving.quantity_consumed !== null || serving.energy_consumed_kcal !== null) {
    return {
      stage: "consumed",
      quantity: serving.quantity_consumed,
      energyKcal: serving.energy_consumed_kcal,
    };
  }
  if (serving.quantity_served !== null || serving.energy_served_kcal !== null) {
    return {
      stage: "served",
      quantity: serving.quantity_served,
      energyKcal: serving.energy_served_kcal,
    };
  }
  if (serving.quantity_planned !== null || serving.energy_planned_kcal !== null) {
    return {
      stage: "planned",
      quantity: serving.quantity_planned,
      energyKcal: serving.energy_planned_kcal,
    };
  }
  return null;
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

function formatDateTime(value: string, timezone: string, locale: Locale): string {
  return new Intl.DateTimeFormat(locale, {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  }).format(new Date(value));
}

function formatNumber(value: string, locale: Locale, maximumFractionDigits = 1): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return value;
  }
  return new Intl.NumberFormat(locale, { maximumFractionDigits }).format(numeric);
}

function participantDisplayName(participant: FamilyMealDetailParticipant): string {
  return [participant.first_name, participant.last_name].filter(Boolean).join(" ");
}

function mealTypeKey(mealType: string) {
  switch (mealType) {
    case "breakfast":
      return "meals.breakfast" as const;
    case "lunch":
      return "meals.lunch" as const;
    case "dinner":
      return "meals.dinner" as const;
    case "snack":
      return "meals.snack" as const;
    default:
      return null;
  }
}

function MealStatus({ status }: { status: string }) {
  const { t } = useI18n();
  let label = status;
  switch (status) {
    case "planned":
      label = t("meals.statusPlanned");
      break;
    case "prepared":
      label = t("meals.statusPrepared");
      break;
    case "served":
      label = t("meals.statusServed");
      break;
    case "completed":
      label = t("meals.statusCompleted");
      break;
    case "cancelled":
      label = t("mealDetail.cancelled");
      break;
    case "replaced":
      label = t("mealDetail.replaced");
      break;
  }
  return <span className={`family-meal-status status-${status}`}>{label}</span>;
}

function participantStatusLabel(status: string, t: ReturnType<typeof useI18n>["t"]): string {
  switch (status) {
    case "planned":
      return t("mealDetail.planned");
    case "served":
      return t("mealDetail.served");
    case "consumed":
      return t("mealDetail.consumed");
    case "partial":
      return t("mealDetail.partial");
    case "skipped":
      return t("mealDetail.skipped");
    case "replaced":
      return t("mealDetail.replaced");
    default:
      return status;
  }
}

function stageLabel(stage: ServingEvidenceStage, t: ReturnType<typeof useI18n>["t"]): string {
  switch (stage) {
    case "consumed":
      return t("mealDetail.consumed");
    case "served":
      return t("mealDetail.served");
    case "planned":
      return t("mealDetail.planned");
  }
}

function ServingRow({ serving }: { serving: FamilyMealDetailServing }) {
  const { locale, t } = useI18n();
  const evidence = currentServingEvidence(serving);

  return (
    <div className="meal-detail-serving">
      <div>
        <strong>{serving.item_name}</strong>
        {evidence ? <small>{stageLabel(evidence.stage, t)}</small> : null}
      </div>
      <div className="meal-detail-serving__values">
        {evidence?.quantity !== null && evidence?.quantity !== undefined ? (
          <span>
            {formatNumber(evidence.quantity, locale)} {serving.quantity_unit ?? ""}
          </span>
        ) : null}
        {evidence?.energyKcal !== null && evidence?.energyKcal !== undefined ? (
          <span>{formatNumber(evidence.energyKcal, locale, 0)} kcal</span>
        ) : null}
        {!evidence ? <span>{t("home.noData")}</span> : null}
      </div>
    </div>
  );
}

function ParticipantCard({ participant }: { participant: FamilyMealDetailParticipant }) {
  const { t } = useI18n();

  return (
    <section className="meal-detail-person">
      <header className="meal-detail-person__header">
        <span className="member-avatar" aria-hidden="true">
          {participant.first_name.slice(0, 1).toUpperCase()}
        </span>
        <div>
          <strong>{participantDisplayName(participant)}</strong>
          <small>{participantStatusLabel(participant.status, t)}</small>
        </div>
      </header>
      {participant.servings.length > 0 ? (
        <div className="meal-detail-servings">
          {participant.servings.map((serving) => (
            <ServingRow key={serving.id} serving={serving} />
          ))}
        </div>
      ) : (
        <div className="meal-detail-no-serving">{t("mealDetail.noServings")}</div>
      )}
    </section>
  );
}

export default function FamilyMealDetailScreen({
  familyId,
  mealEventId,
  onBack,
}: {
  familyId: string;
  mealEventId: string;
  onBack: () => void;
}) {
  const { locale, t } = useI18n();
  const [detail, setDetail] = useState<FamilyMealDetail | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setBusy(true);
    setError(null);
    void getFamilyMealDetail(familyId, mealEventId)
      .then((result) => {
        if (!cancelled) {
          setDetail(result);
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setDetail(null);
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
  }, [familyId, mealEventId]);

  if (busy) {
    return (
      <div className="family-meal-detail">
        <button className="button ghost detail-back" onClick={onBack} type="button">
          ← {t("mealDetail.back")}
        </button>
        <div className="shell-loading" role="status">
          {t("mealDetail.loading")}
        </div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="family-meal-detail">
        <button className="button ghost detail-back" onClick={onBack} type="button">
          ← {t("mealDetail.back")}
        </button>
        <div className="error-banner" role="alert">
          <strong>{t("error.title")}</strong>
          <span>{error ?? t("home.noData")}</span>
        </div>
      </div>
    );
  }

  const typeKey = mealTypeKey(detail.meal_type);
  const fallbackTitle = typeKey ? t(typeKey) : detail.meal_type;

  return (
    <div className="family-meal-detail">
      <button className="button ghost detail-back" onClick={onBack} type="button">
        ← {t("mealDetail.back")}
      </button>

      <header className="screen-header compact-screen-header meal-detail-header">
        <div>
          <span className="eyebrow">{t("mealDetail.eyebrow")}</span>
          <h1>{detail.title ?? fallbackTitle}</h1>
          <p className="meal-detail-meta">
            <span>{formatDateTime(detail.scheduled_at, detail.timezone, locale)}</span>
            {detail.location ? <span>{detail.location}</span> : null}
          </p>
        </div>
        <MealStatus status={detail.status} />
      </header>

      <section className="meal-detail-section-heading">
        <div>
          <h2>{t("mealDetail.portions")}</h2>
          <p>{t("mealDetail.portionsHelp")}</p>
        </div>
        <span>
          {detail.participants.length} {t("mealDetail.participants")}
        </span>
      </section>

      <div className="meal-detail-people">
        {detail.participants.map((participant) => (
          <ParticipantCard key={participant.person_id} participant={participant} />
        ))}
      </div>
    </div>
  );
}
