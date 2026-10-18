import {getFamilyMealPlan} from "./api/client";
import {listRecipeReviews,type ReviewRecipe} from "./api/dietaryReviewClient";
import {foodAlternativeNames,calendarDateOffset} from "./mealAlternatives";
import IngredientAlternativeLine from "./IngredientAlternativeLine";
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
import { listRetailAlternatives, type RetailAlternative } from "./api/planningWorkspaceClient";
import RetailAlternativeCards from "./RetailAlternativeCards";
import ShoppingProductChoice from "./ShoppingProductChoice";
import ShoppingReceiptEntry from "./ShoppingReceiptEntry";
import "./planning-journey.css";

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

export function shoppingIssueLabel(issue: string, pt: boolean): string {
  const name = issue.match(/Recipe '([^']+)'/)?.[1];
  if (name && issue.includes("estimated serving count")) return pt ? `${name}: quantidades aproximadas. Confirma o número de porções que a receita rende antes de comprar.` : `${name}: approximate quantities. Confirm the recipe yield before buying.`;
  if (name && issue.includes("needs yield evidence")) return pt ? `${name}: falta indicar quantas porções rende a receita para calcular as compras.` : `${name}: recipe yield is needed to calculate shopping.`;
  const food = issue.match(/Ingredient '([^']+)'/)?.[1];
  if (food && issue.includes("incompatible planned units")) return pt ? `${food}: as unidades das receitas não são compatíveis. Confirma o peso ou volume de cada embalagem.` : `${food}: recipe units differ. Confirm each package weight or volume.`;
  return issue;
}

type EditValues = { name: string; quantity: string; unit: string };

export function formatShoppingQuantity(value:string,locale:string):string {
  const number=Number(value);
  return value.trim() && Number.isFinite(number) ? new Intl.NumberFormat(locale,{maximumFractionDigits:6}).format(number) : value;
}

export default function ShoppingListScreen({ familyId, initialStartDate }: { familyId: string; initialStartDate?: string }) {
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

  const [planRecipes,setPlanRecipes]=useState<ReviewRecipe[]>([]);
  const [alternativesError,setAlternativesError]=useState(false);
  const [data, setData] = useState<ShoppingList | null>(null);
  const [startDate, setStartDate] = useState(initialStartDate ?? today());
  const [retail, setRetail] = useState<RetailAlternative[]>([]);
  const [retailError, setRetailError] = useState("");
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
        if (result.planning_start && !initialStartDate) {
          setStartDate(result.planning_start);
        }
        if (result.planning_start && result.planning_end && !initialStartDate) {
          const start = new Date(`${result.planning_start}T00:00:00Z`);
          const end = new Date(`${result.planning_end}T00:00:00Z`);
          setDays(Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1);
        }
      })
      .catch((caught: unknown) => setError(errorText(caught)))
      .finally(() => setBusy(false));
  }

  useEffect(load, [familyId]);
  useEffect(() => {
    let cancelled = false;
    setRetail([]);
    setRetailError("");
    void listRetailAlternatives(familyId).then(rows => {if (!cancelled) setRetail(rows);})
      .catch(e => {if (!cancelled) setRetailError(String(e));});
    return () => {cancelled = true;};
  }, [familyId]);

  useEffect(()=>{
    let cancelled=false;setPlanRecipes([]);setAlternativesError(false);
    if(!data?.planning_start || !data.planning_end) return;
    const count=Math.round((Date.parse(data.planning_end)-Date.parse(data.planning_start))/86400000)+1;
    if(count<1||count>366)return;
    const requests=Array.from({length:Math.ceil(count/14)},(_,index)=>getFamilyMealPlan(familyId,calendarDateOffset(data.planning_start!,index*14),Math.min(14,count-index*14)));
    void Promise.all([listRecipeReviews(familyId),Promise.all(requests)]).then(([reviews,plans])=>{
      if(cancelled)return;
      const ids=new Set(plans.flatMap(p=>p.days.flatMap(d=>d.slots.flatMap(slot=>slot.meals.filter(m=>m.status!=="cancelled").map(m=>m.recipe_id)))));
      setPlanRecipes(reviews.filter(r=>ids.has(r.id)));
    }).catch(()=>{if(!cancelled)setAlternativesError(true);});
    return()=>{cancelled=true;};
  },[familyId,data?.planning_start,data?.planning_end,data?.generated_at]);

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
      {retailError ? <p role="alert">{locale === "pt-PT" ? "Não foi possível carregar alternativas de supermercado: " : "Could not load supermarket alternatives: "}{retailError}</p> : null}
      {data && initialStartDate && data.planning_start !== initialStartDate ? <p role="alert" className="error-banner">{locale === "pt-PT" ? "Esta lista ainda pertence a outro período. Usa «Atualizar» para calcular as compras da semana escolhida." : "This list belongs to another period. Refresh to calculate shopping for the chosen week."}</p> : null}
      {busy && !data ? <div className="shell-loading">{copy.loading}</div> : null}

      {data ? (
        <>
          {data.planning_issues.length > 0 ? (
            <section className="shopping-issues">
              <strong>{copy.issues}</strong>
              <ul>{data.planning_issues.map((issue) => <li key={issue}>{shoppingIssueLabel(issue, locale === "pt-PT")}</li>)}</ul>
            </section>
          ) : null}

          <section className="shopping-requirements">
            <h2>{copy.needs}</h2>
            {data.requirements.length === 0 ? <div className="empty-card">{copy.noRequirements}</div> : null}
            {data.requirements.map((requirement) => (
              <div className="requirement-row" key={requirement.food_item_id}>
                <IngredientAlternativeLine name={requirement.food_item_name} alternatives={foodAlternativeNames(planRecipes,requirement.food_item_id)}/>
                <span>{formatShoppingQuantity(requirement.required_quantity,locale)} {requirement.unit} {copy.required}</span>
                <span>{formatShoppingQuantity(requirement.available_quantity,locale)} {requirement.unit} {copy.stock}</span>
                <span>{formatShoppingQuantity(requirement.missing_quantity,locale)} {requirement.unit} {copy.missing}</span>
              </div>
            ))}
          </section>

          <section className="shopping-list-section">
            <h2>{copy.list}</h2>
            {alternativesError && <p role="status">{locale==="pt-PT"?"Não foi possível carregar as alternativas deste plano.":"Alternatives for this plan could not be loaded."}</p>}
            {data.items.some(i=>i.status==="needed"&&foodAlternativeNames(planRecipes,i.food_item_id).length>0)&&<p className="journey-context">{locale==="pt-PT"?"As trocas marcadas «por aplicar» são propostas. As quantidades abaixo ainda pertencem à receita original; aplica uma variante validada no plano para atualizar as compras.":"Changes marked not applied are proposals. Quantities still belong to the original recipe; apply a validated variant in the plan to update shopping."}</p>}
            {data.items.length === 0 ? <div className="empty-card">{copy.empty}</div> : null}
            {data.items.map((item) => (
              <article className={`shopping-item ${item.status === "purchased" ? "purchased" : ""}`} key={item.id}>
                <label className="shopping-check">
                  <input
                    checked={item.status === "purchased"}
                    disabled={busy || !!item.pantry_receipt}
                    onChange={() => void toggle(item)}
                    type="checkbox"
                  />
                  <span>
                    <IngredientAlternativeLine name={item.name} alternatives={item.status==="needed"?foodAlternativeNames(planRecipes,item.food_item_id):[]}/>
                    {item.quantity ? <small>{formatShoppingQuantity(item.quantity,locale)} {item.unit}</small> : null}
                  </span>
                </label>
                <span className="status-chip">{item.item_source === "automatic" ? copy.automatic : copy.manual}</span>
                <div className="row-actions">
                  <button disabled={!!item.pantry_receipt} className="button ghost small" aria-label={`${copy.edit}: ${item.name}`} onClick={() => startEdit(item)} type="button">{copy.edit}</button>
                  <button disabled={!!item.pantry_receipt} className="button ghost small" aria-label={`${copy.remove}: ${item.name}`} onClick={() => void remove(item)} type="button">{copy.remove}</button>
                </div>
                <ShoppingReceiptEntry key={`${familyId}:${item.id}`} familyId={familyId} item={item} onChanged={setData} disabled={busy}/>
                <ShoppingProductChoice familyId={familyId} item={item} products={retail} onChanged={setData} disabled={busy}/>
                {item.food_item_id && item.status === "needed" && retail.some(p=>p.applicable_food_item_ids.includes(item.food_item_id!)) ? <details className="shopping-retail"><summary>{locale === "pt-PT" ? "Ver alternativas e rótulos de supermercado" : "View supermarket alternatives and labels"}</summary><RetailAlternativeCards familyId={familyId} onConfirmed={()=>{void listRetailAlternatives(familyId).then(setRetail).catch(e=>setRetailError(String(e)));}} products={retail.filter(p => p.applicable_food_item_ids.includes(item.food_item_id!))}/>{!retail.some(p => p.applicable_food_item_ids.includes(item.food_item_id!)) && <p>{locale === "pt-PT" ? "Ainda não há um produto pesquisado para este ingrediente." : "No researched product for this ingredient yet."}</p>}</details> : null}
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
            <input aria-label={copy.name} placeholder={copy.name} value={manualName} onChange={(event) => setManualName(event.target.value)} />
            <input aria-label={copy.quantity} placeholder={copy.quantity} value={manualQuantity} onChange={(event) => setManualQuantity(event.target.value)} />
            <input aria-label={copy.unit} placeholder={copy.unit} value={manualUnit} onChange={(event) => setManualUnit(event.target.value)} />
            <button className="button primary" disabled={busy} type="submit">{copy.add}</button>
          </form>
        </>
      ) : null}
    </div>
  );
}
