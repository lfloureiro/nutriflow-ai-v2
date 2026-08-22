import { useEffect, useMemo, useState, type FormEvent } from "react";

import { ApiError, listFamilyIngredients } from "./api/client";
import type { Ingredient } from "./api/ingredientTypes";
import {
  createPantryLot,
  deactivatePantryLot,
  listPantryLots,
  updatePantryLot,
} from "./api/pantryShoppingClient";
import type { PantryLot } from "./api/pantryShoppingTypes";
import { useI18n } from "./i18n";

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.message} (HTTP ${error.status})`;
  }
  return error instanceof Error ? error.message : String(error);
}

function decimalText(value: string): string {
  return value.trim().replace(",", ".");
}

type FormValues = {
  ingredientId: string;
  quantity: string;
  unit: string;
  location: string;
  expiresAt: string;
};

const EMPTY_FORM: FormValues = {
  ingredientId: "",
  quantity: "",
  unit: "g",
  location: "",
  expiresAt: "",
};

export default function PantryScreen({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const copy =
    locale === "pt-PT"
      ? {
          eyebrow: "Casa",
          title: "Despensa",
          help: "Stock disponível para as refeições planeadas.",
          add: "Adicionar stock",
          save: "Guardar",
          cancel: "Cancelar",
          ingredient: "Ingrediente",
          quantity: "Quantidade",
          unit: "Unidade",
          location: "Local",
          expires: "Validade",
          showInactive: "Mostrar inativos",
          empty: "Ainda não há stock registado.",
          inactive: "Inativo",
          deactivate: "Retirar do stock",
          reactivate: "Reativar",
          edit: "Editar",
          loading: "A carregar despensa…",
        }
      : {
          eyebrow: "Home",
          title: "Pantry",
          help: "Available stock for planned meals.",
          add: "Add stock",
          save: "Save",
          cancel: "Cancel",
          ingredient: "Ingredient",
          quantity: "Quantity",
          unit: "Unit",
          location: "Location",
          expires: "Expiry",
          showInactive: "Show inactive",
          empty: "No pantry stock yet.",
          inactive: "Inactive",
          deactivate: "Remove from stock",
          reactivate: "Reactivate",
          edit: "Edit",
          loading: "Loading pantry…",
        };

  const [lots, setLots] = useState<PantryLot[]>([]);
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [editing, setEditing] = useState<PantryLot | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [values, setValues] = useState<FormValues>(EMPTY_FORM);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeIngredients = useMemo(
    () => ingredients.filter((ingredient) => ingredient.is_active),
    [ingredients],
  );

  function load() {
    setBusy(true);
    setError(null);
    void Promise.all([
      listPantryLots(familyId, includeInactive),
      listFamilyIngredients(familyId),
    ])
      .then(([nextLots, nextIngredients]) => {
        setLots(nextLots);
        setIngredients(nextIngredients);
      })
      .catch((caught: unknown) => setError(errorText(caught)))
      .finally(() => setBusy(false));
  }

  useEffect(load, [familyId, includeInactive]);

  function startCreate() {
    setEditing(null);
    setValues({ ...EMPTY_FORM, ingredientId: activeIngredients[0]?.id ?? "" });
    setShowForm(true);
  }

  function startEdit(lot: PantryLot) {
    setEditing(lot);
    setValues({
      ingredientId: lot.food_item_id,
      quantity: lot.quantity_available,
      unit: lot.unit,
      location: lot.location ?? "",
      expiresAt: lot.expires_at?.slice(0, 10) ?? "",
    });
    setShowForm(true);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!values.ingredientId || Number(decimalText(values.quantity)) <= 0) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (editing) {
        await updatePantryLot(familyId, editing.id, {
          quantity_available: decimalText(values.quantity),
          unit: values.unit,
          location: values.location || null,
          expires_at: values.expiresAt ? `${values.expiresAt}T23:59:59Z` : null,
        });
      } else {
        await createPantryLot(familyId, {
          food_item_id: values.ingredientId,
          quantity_available: decimalText(values.quantity),
          unit: values.unit,
          location: values.location || null,
          expires_at: values.expiresAt ? `${values.expiresAt}T23:59:59Z` : null,
        });
      }
      setShowForm(false);
      setEditing(null);
      load();
    } catch (caught: unknown) {
      setError(errorText(caught));
      setBusy(false);
    }
  }

  async function changeAvailability(lot: PantryLot) {
    setBusy(true);
    setError(null);
    try {
      if (lot.is_available) {
        await deactivatePantryLot(familyId, lot.id);
      } else {
        await updatePantryLot(familyId, lot.id, { is_available: true });
      }
      load();
    } catch (caught: unknown) {
      setError(errorText(caught));
      setBusy(false);
    }
  }

  return (
    <div className="pantry-screen">
      <header className="screen-header compact-screen-header">
        <div>
          <span className="eyebrow">{copy.eyebrow}</span>
          <h1>{copy.title}</h1>
          <p>{copy.help}</p>
        </div>
        <button className="button primary" onClick={startCreate} type="button">
          {copy.add}
        </button>
      </header>

      <label className="pantry-toggle">
        <input
          checked={includeInactive}
          onChange={(event) => setIncludeInactive(event.target.checked)}
          type="checkbox"
        />
        <span>{copy.showInactive}</span>
      </label>

      {error ? <div className="error-banner">{error}</div> : null}
      {busy && lots.length === 0 ? <div className="shell-loading">{copy.loading}</div> : null}

      {showForm ? (
        <form className="house-editor-card pantry-editor" onSubmit={save}>
          <label className="field">
            <span>{copy.ingredient}</span>
            <select
              disabled={editing !== null}
              value={values.ingredientId}
              onChange={(event) => setValues((v) => ({ ...v, ingredientId: event.target.value }))}
            >
              <option value="">—</option>
              {activeIngredients.map((ingredient) => (
                <option key={ingredient.id} value={ingredient.id}>
                  {ingredient.name}
                </option>
              ))}
            </select>
          </label>
          <div className="two-column-fields">
            <label className="field">
              <span>{copy.quantity}</span>
              <input
                inputMode="decimal"
                value={values.quantity}
                onChange={(event) => setValues((v) => ({ ...v, quantity: event.target.value }))}
              />
            </label>
            <label className="field">
              <span>{copy.unit}</span>
              <input
                value={values.unit}
                onChange={(event) => setValues((v) => ({ ...v, unit: event.target.value }))}
              />
            </label>
          </div>
          <div className="two-column-fields">
            <label className="field">
              <span>{copy.location}</span>
              <input
                value={values.location}
                onChange={(event) => setValues((v) => ({ ...v, location: event.target.value }))}
              />
            </label>
            <label className="field">
              <span>{copy.expires}</span>
              <input
                type="date"
                value={values.expiresAt}
                onChange={(event) => setValues((v) => ({ ...v, expiresAt: event.target.value }))}
              />
            </label>
          </div>
          <div className="editor-actions">
            <button className="button primary" disabled={busy} type="submit">
              {copy.save}
            </button>
            <button className="button ghost" onClick={() => setShowForm(false)} type="button">
              {copy.cancel}
            </button>
          </div>
        </form>
      ) : null}

      <div className="pantry-list">
        {!busy && lots.length === 0 ? <div className="empty-card">{copy.empty}</div> : null}
        {lots.map((lot) => (
          <article className={`pantry-row ${lot.is_available ? "" : "inactive"}`} key={lot.id}>
            <div>
              <strong>{lot.food_item_name}</strong>
              <span>
                {lot.quantity_available} {lot.unit}
                {lot.location ? ` · ${lot.location}` : ""}
              </span>
              {lot.expires_at ? <small>{copy.expires}: {lot.expires_at.slice(0, 10)}</small> : null}
            </div>
            <div className="row-actions">
              {!lot.is_available ? <span className="status-chip">{copy.inactive}</span> : null}
              <button className="button ghost small" onClick={() => startEdit(lot)} type="button">
                {copy.edit}
              </button>
              <button
                className="button ghost small"
                onClick={() => void changeAvailability(lot)}
                type="button"
              >
                {lot.is_available ? copy.deactivate : copy.reactivate}
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
