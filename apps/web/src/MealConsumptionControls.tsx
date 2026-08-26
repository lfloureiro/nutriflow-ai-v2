import { useEffect, useState } from "react";

import { ApiError } from "./api/client";
import {
  recordMealConsumption,
  recordMealParticipantConsumption,
} from "./api/mealConsumptionClient";
import type { MealPlanEntry, MealPlanParticipant } from "./api/mealPlanTypes";
import { useI18n } from "./i18n";

const COPY = {
  "pt-PT": {
    planned: "Planeado",
    consumed: "Consumido",
    partial: "Parcial",
    skipped: "Não comido",
    all: "Comi tudo",
    part: "Parte",
    none: "Não comi",
    quantity: "Qtd. comida",
    portion: "dose",
    savePart: "Guardar",
    kcal: "kcal",
    error: "Não foi possível registar",
  },
  en: {
    planned: "Planned",
    consumed: "Consumed",
    partial: "Partial",
    skipped: "Not eaten",
    all: "Ate all",
    part: "Part",
    none: "Did not eat",
    quantity: "Amount eaten",
    portion: "serving",
    savePart: "Save",
    kcal: "kcal",
    error: "Could not record consumption",
  },
} as const;

function errorText(error: unknown): string {
  if (error instanceof ApiError) return `${error.message} (HTTP ${error.status})`;
  return error instanceof Error ? error.message : String(error);
}

function personName(participant: MealPlanParticipant): string {
  return [participant.first_name, participant.last_name].filter(Boolean).join(" ");
}

function statusText(status: string, copy: (typeof COPY)["pt-PT"] | (typeof COPY)["en"]): string {
  if (status === "consumed") return copy.consumed;
  if (status === "partial") return copy.partial;
  if (status === "skipped") return copy.skipped;
  return copy.planned;
}

export default function MealConsumptionControls({
  familyId,
  entry,
  participant,
  onUpdated,
}: {
  familyId: string;
  entry: MealPlanEntry;
  participant: MealPlanParticipant;
  onUpdated: () => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const legacyBreakfast = !participant.serving_id && entry.meal_type === "breakfast";
  const initialQuantity =
    participant.quantity_consumed ?? participant.quantity ?? (legacyBreakfast ? "0.5" : "");
  const [partialOpen, setPartialOpen] = useState(false);
  const [quantity, setQuantity] = useState(initialQuantity);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setQuantity(
      participant.quantity_consumed ?? participant.quantity ?? (legacyBreakfast ? "0.5" : ""),
    );
  }, [legacyBreakfast, participant.quantity, participant.quantity_consumed]);

  async function record(status: "consumed" | "partial" | "skipped") {
    const normalized = quantity.trim().replace(",", ".");
    if (status === "partial" && !normalized) {
      setPartialOpen(true);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const payload = {
        status,
        quantity_consumed: status === "partial" ? normalized : null,
      } as const;
      if (participant.serving_id) {
        await recordMealConsumption(
          familyId,
          entry.id,
          participant.person_id,
          participant.serving_id,
          payload,
        );
      } else {
        await recordMealParticipantConsumption(
          familyId,
          entry.id,
          participant.person_id,
          payload,
        );
      }
      setPartialOpen(false);
      onUpdated();
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  if (!participant.serving_id && !legacyBreakfast) return null;

  const realized = ["consumed", "partial", "skipped"].includes(participant.status);
  const quantityUnit = participant.unit ?? (legacyBreakfast ? copy.portion : null);
  return (
    <div className="meal-consumption-row">
      <div className="meal-consumption-person">
        <strong>{personName(participant)}</strong>
        <span>
          {statusText(participant.status, copy)}
          {participant.energy_consumed_kcal
            ? ` · ${Math.round(Number(participant.energy_consumed_kcal))} ${copy.kcal}`
            : participant.energy_kcal
              ? ` · ${Math.round(Number(participant.energy_kcal))} ${copy.kcal} ${copy.planned.toLowerCase()}`
              : ""}
        </span>
      </div>
      <div className="meal-consumption-actions">
        <button
          className="button ghost compact"
          disabled={busy}
          onClick={() => void record("consumed")}
          type="button"
        >
          {copy.all}
        </button>
        <button
          className="button ghost compact"
          disabled={busy}
          onClick={() => setPartialOpen((current) => !current)}
          type="button"
        >
          {copy.part}
        </button>
        <button
          className="button ghost compact"
          disabled={busy}
          onClick={() => void record("skipped")}
          type="button"
        >
          {copy.none}
        </button>
      </div>
      {partialOpen ? (
        <div className="meal-consumption-partial">
          <label className="field">
            <span>{copy.quantity}{quantityUnit ? ` (${quantityUnit})` : ""}</span>
            <input
              autoFocus
              inputMode="decimal"
              min="0.0001"
              step="0.01"
              type="number"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
            />
          </label>
          <button
            className="button primary compact"
            disabled={busy || !quantity.trim()}
            onClick={() => void record("partial")}
            type="button"
          >
            {copy.savePart}
          </button>
        </div>
      ) : null}
      {realized ? (
        <span className="meal-consumption-state">{statusText(participant.status, copy)}</span>
      ) : null}
      {error ? (
        <span className="meal-consumption-error">{copy.error}: {error}</span>
      ) : null}
    </div>
  );
}
