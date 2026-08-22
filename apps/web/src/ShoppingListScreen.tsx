import { useEffect, useState, type FormEvent } from "react";

import { ApiError } from "./api/client";
import {
  addShoppingItem,
  deleteShoppingItem,
  getShoppingList,
  refreshShoppingList,
  updateShoppingItem,
} from "./api/pantryShoppingClient";
import type { ShoppingList, ShoppingListItem } from "./api/pantryShoppingTypes";
import { useI18n } from "./i18n";

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.message} (HTTP ${error.status})`;
  }
  return error instanceof Error ? error.message : String(error);
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function decimalText(value: string): string {
  return value.trim().replace(",", ".");
}

type EditValues = { name: string; quantity: string; unit: string };

export default function ShoppingListScreen({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const copy =
    locale === "pt-PT"
      ? {
          eyebrow: "Casa",
          title: "Compras",
          help: "Faltas do plano, depois de descontar o stock da despensa.",
          start: "Desde",
          days: "Dias",
          refresh: "Atualizar a partir do plano",
          needs: "Necessidades do plano",
          required: "necessário",
          stock: "em stock",
          missing: "falta",
          list: "Lista de compras",
          addManual: "Adicionar item manual",
          name: "Item",
          quantity: "Quantidade",
          unit: "Unidade",
          add: "Adicionar",
          edit: "Editar",
          save: "Guardar",
          cancel: "Cancelar",
          remove: "Remover",
          purchased: "Comprado",
          automatic: "Plano",
          manual: "Manual",
          empty: "A lista está vazia.",
          noRequirements: "Não há faltas calculadas para este intervalo.",
          issues: "Não foi possível calcular completamente",
          loading: "A carregar compras…",
        }
      : {
          eyebrow: "Home",
          title: "Shopping",
          help: "Plan requirements after subtracting pantry stock.",
          start: "From",
          days: "Days",
          refresh: "Refresh from plan",
          needs: "Plan requirements",
          required: "required",
          stock: "in stock",
          missing: "missing",
          list: "Shopping list",
          addManual: "Add manual item",
          name: "Item",
          quantity: "Quantity",
          unit: "Unit",
          add: "Add",
          edit: "Edit",
          save: "Save",
          cancel: "Cancel",
          remove: "Remove",
          purchased: "Purchased",
          automatic: "Plan",
          manual: "Manual",
          empty: "The list is empty.",
          noRequirements: "No calculated shortages for this range.",
          issues: "Could not calculate completely",
          loading: "Loading shopping list…",
        };

  const [data, setData] = useState<ShoppingList | null>(null);
  const [startDate, setStartDate] = useState(today());
  const [days, setDays] = useState(7);
  const [manualName, setManualName] = useState("");
  const [manualQuantity, setManualQuantity] = useState("");
  const [manualUnit, setManualUnit] = useState("");
  const [editing, setEditing] = useState<ShoppingListItem | null>(null);
  const [editValues, setEditValues] = useState<EditValues>({ name: "", quantity: "", unit: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setBusy(true);
    setError(null);
    void getShoppingList(familyId)
      .then((result) => {
        setData(result);
        if (result.planning_start) {
          setStartDate(result.planning_start);
        }
        if (result.planning_start && result.planning_end) {
          const start = new Date(`${result.planning_start}T00:00:00Z`);
          const end = new Date(`${result.planning_end}T00:00:00Z`);
          setDays(Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1);
        }
      })
      .catch((caught: unknown) => setError(errorText(caught)))
      .finally(() => setBusy(false));
  }

  useEffect(load, [familyId]);

  async function refresh() {
    setBusy(true);
    setError(null);
    try {
      setData(await refreshShoppingList(familyId, startDate, days));
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  async function addManual(event: FormEvent) {
    event.preventDefault();
    if (!manualName.trim()) {
      return;
    }
    const hasQuantity = manualQuantity.trim().length > 0;
    if (hasQuantity !== (manualUnit.trim().length > 0)) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setData(
        await addShoppingItem(familyId, {
          name: manualName.trim(),
          quantity: hasQuantity ? decimalText(manualQuantity) : null,
          unit: hasQuantity ? manualUnit.trim() : null,
        }),
      );
      setManualName("");
      setManualQuantity("");
      setManualUnit("");
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  async function toggle(item: ShoppingListItem) {
    setBusy(true);
    try {
      setData(
        await updateShoppingItem(familyId, item.id, {
          status: item.status === "needed" ? "purchased" : "needed",
        }),
      );
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  function startEdit(item: ShoppingListItem) {
    setEditing(item);
    setEditValues({
      name: item.name,
      quantity: item.quantity ?? "",
      unit: item.unit ?? "",
    });
  }

  async function saveEdit(event: FormEvent) {
    event.preventDefault();
    if (!editing || !editValues.name.trim()) {
      return;
    }
    const hasQuantity = editValues.quantity.trim().length > 0;
    if (hasQuantity !== (editValues.unit.trim().length > 0)) {
      return;
    }
    setBusy(true);
    try {
      setData(
        await updateShoppingItem(familyId, editing.id, {
          name: editValues.name.trim(),
          quantity: hasQuantity ? decimalText(editValues.quantity) : null,
          unit: hasQuantity ? editValues.unit.trim() : null,
        }),
      );
      setEditing(null);
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  async function remove(item: ShoppingListItem) {
    setBusy(true);
    try {
      await deleteShoppingItem(familyId, item.id);
      load();
    } catch (caught: unknown) {
      setError(errorText(caught));
      setBusy(false);
    }
  }

  return (
    <div className="shopping-screen">
      <header className="screen-header compact-screen-header">
        <div>
          <span className="eyebrow">{copy.eyebrow}</span>
          <h1>{copy.title}</h1>
          <p>{copy.help}</p>
        </div>
      </header>

      <section className="shopping-refresh-card">
        <label className="field compact-field">
          <span>{copy.start}</span>
          <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
        </label>
        <label className="field compact-field">
          <span>{copy.days}</span>
          <select value={days} onChange={(event) => setDays(Number(event.target.value))}>
            <option value={1}>1</option>
            <option value={7}>7</option>
            <option value={14}>14</option>
          </select>
        </label>
        <button className="button primary" disabled={busy} onClick={() => void refresh()} type="button">
          {copy.refresh}
        </button>
      </section>

      {error ? <div className="error-banner">{error}</div> : null}
      {busy && !data ? <div className="shell-loading">{copy.loading}</div> : null}

      {data ? (
        <>
          {data.planning_issues.length > 0 ? (
            <section className="shopping-issues">
              <strong>{copy.issues}</strong>
              <ul>{data.planning_issues.map((issue) => <li key={issue}>{issue}</li>)}</ul>
            </section>
          ) : null}

          <section className="shopping-requirements">
            <h2>{copy.needs}</h2>
            {data.requirements.length === 0 ? <div className="empty-card">{copy.noRequirements}</div> : null}
            {data.requirements.map((requirement) => (
              <div className="requirement-row" key={requirement.food_item_id}>
                <strong>{requirement.food_item_name}</strong>
                <span>{requirement.required_quantity} {requirement.unit} {copy.required}</span>
                <span>{requirement.available_quantity} {requirement.unit} {copy.stock}</span>
                <span>{requirement.missing_quantity} {requirement.unit} {copy.missing}</span>
              </div>
            ))}
          </section>

          <section className="shopping-list-section">
            <h2>{copy.list}</h2>
            {data.items.length === 0 ? <div className="empty-card">{copy.empty}</div> : null}
            {data.items.map((item) => (
              <article className={`shopping-item ${item.status === "purchased" ? "purchased" : ""}`} key={item.id}>
                <label className="shopping-check">
                  <input
                    checked={item.status === "purchased"}
                    disabled={busy}
                    onChange={() => void toggle(item)}
                    type="checkbox"
                  />
                  <span>
                    <strong>{item.name}</strong>
                    {item.quantity ? <small>{item.quantity} {item.unit}</small> : null}
                  </span>
                </label>
                <span className="status-chip">{item.item_source === "automatic" ? copy.automatic : copy.manual}</span>
                <div className="row-actions">
                  <button className="button ghost small" onClick={() => startEdit(item)} type="button">{copy.edit}</button>
                  <button className="button ghost small" onClick={() => void remove(item)} type="button">{copy.remove}</button>
                </div>
              </article>
            ))}
          </section>

          {editing ? (
            <form className="house-editor-card shopping-edit-card" onSubmit={saveEdit}>
              <label className="field">
                <span>{copy.name}</span>
                <input value={editValues.name} onChange={(event) => setEditValues((v) => ({ ...v, name: event.target.value }))} />
              </label>
              <div className="two-column-fields">
                <label className="field">
                  <span>{copy.quantity}</span>
                  <input value={editValues.quantity} onChange={(event) => setEditValues((v) => ({ ...v, quantity: event.target.value }))} />
                </label>
                <label className="field">
                  <span>{copy.unit}</span>
                  <input value={editValues.unit} onChange={(event) => setEditValues((v) => ({ ...v, unit: event.target.value }))} />
                </label>
              </div>
              <div className="editor-actions">
                <button className="button primary" type="submit">{copy.save}</button>
                <button className="button ghost" onClick={() => setEditing(null)} type="button">{copy.cancel}</button>
              </div>
            </form>
          ) : null}

          <form className="shopping-manual-form" onSubmit={addManual}>
            <strong>{copy.addManual}</strong>
            <input placeholder={copy.name} value={manualName} onChange={(event) => setManualName(event.target.value)} />
            <input placeholder={copy.quantity} value={manualQuantity} onChange={(event) => setManualQuantity(event.target.value)} />
            <input placeholder={copy.unit} value={manualUnit} onChange={(event) => setManualUnit(event.target.value)} />
            <button className="button primary" disabled={busy} type="submit">{copy.add}</button>
          </form>
        </>
      ) : null}
    </div>
  );
}
