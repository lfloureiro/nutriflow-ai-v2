import {EmptyState} from "./ui/primitives";
import {pantryState,visiblePantryLots} from "./pantryDisplay";
import Icon from "./ui/Icon";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import ContextDrawer from "./ui/ContextDrawer";
import { registerNavigationBlocker } from "./navigation";

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
  const [query,setQuery]=useState("");
  const [filter,setFilter]=useState<"all"|"soon"|"undated">("all");
  const [now,setNow]=useState(()=>Date.now());
  useEffect(()=>{const timer=window.setInterval(()=>setNow(Date.now()),60_000);return()=>window.clearInterval(timer);},[]);
  const shown=visiblePantryLots(lots,query,filter,now);
  const attention=lots.filter(lot=>["soon","expired"].includes(pantryState(lot,now))).length;
  const undated=lots.filter(lot=>pantryState(lot,now)==="undated").length;
  const [values, setValues] = useState<FormValues>(EMPTY_FORM);
  const [initialValues, setInitialValues] = useState<FormValues>(EMPTY_FORM);
  const draftDirty = showForm && JSON.stringify(values) !== JSON.stringify(initialValues);
  const draftDirtyRef = useRef(draftDirty);
  draftDirtyRef.current = draftDirty;
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(busy);
  busyRef.current = busy;
  const confirmDiscard = () => !draftDirtyRef.current || window.confirm(
    locale === "pt-PT"
      ? "Tens alterações de stock por guardar. Descartá-las?"
      : "You have unsaved pantry changes. Discard them?",
  );
  useEffect(() => {
    const release = registerNavigationBlocker(confirmDiscard);
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (!draftDirtyRef.current) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", beforeUnload);
    return () => { release(); window.removeEventListener("beforeunload", beforeUnload); };
  }, [locale]);
  function closeForm(): boolean {
    if (busyRef.current || !confirmDiscard()) return false;
    setShowForm(false);
    setEditing(null);
    return true;
  }
  const [error, setError] = useState<string | null>(null);

  const activeIngredients = useMemo(
    () => ingredients.filter((ingredient) => ingredient.is_active || ingredient.id===editing?.food_item_id),
    [ingredients,editing?.food_item_id],
  );

  function load() {
    let cancelled=false;
    setBusy(true);
    setError(null);
    void Promise.all([
      listPantryLots(familyId, includeInactive),
      listFamilyIngredients(familyId),
    ])
      .then(([nextLots, nextIngredients]) => {
        if(cancelled)return;
        setLots(nextLots);
        setIngredients(nextIngredients);
      })
      .catch((caught: unknown) => {if(!cancelled)setError(errorText(caught));})
      .finally(() => {if(!cancelled)setBusy(false);});
    return()=>{cancelled=true;};
  }

  useEffect(load, [familyId, includeInactive]);

  function startCreate() {
    setEditing(null);
    const next = { ...EMPTY_FORM, ingredientId: activeIngredients.find(ingredient=>ingredient.is_active)?.id ?? "" };
    setValues(next);
    setInitialValues(next);
    setShowForm(true);
  }

  function startEdit(lot: PantryLot) {
    setEditing(lot);
    const next = {
      ingredientId: lot.food_item_id,
      quantity: lot.quantity_available,
      unit: lot.unit,
      location: lot.location ?? "",
      expiresAt: lot.expires_at?.slice(0, 10) ?? "",
    };
    setValues(next);
    setInitialValues(next);
    setShowForm(true);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!values.ingredientId || !values.quantity.trim() || !Number.isFinite(Number(decimalText(values.quantity))) || Number(decimalText(values.quantity)) <= 0 || !values.unit.trim()) {
      setError(locale === "pt-PT" ? "Escolhe um ingrediente e indica uma quantidade positiva e a unidade." : "Choose an ingredient, a positive quantity and a unit.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (editing) {
        await updatePantryLot(familyId, editing.id, {
          quantity_available: decimalText(values.quantity),
          unit: values.unit.trim(),
          location: values.location || null,
          expires_at: values.expiresAt ? `${values.expiresAt}T23:59:59Z` : null,
        });
      } else {
        await createPantryLot(familyId, {
          food_item_id: values.ingredientId,
          quantity_available: decimalText(values.quantity),
          unit: values.unit.trim(),
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
    <div className="pantry-screen" aria-busy={busy}>
      <header className="screen-header compact-screen-header">
        <div>
          <span className="eyebrow">{copy.eyebrow}</span>
          <h1>{copy.title}</h1>
          <p>{copy.help}</p>
        </div>
        <button className="button primary" disabled={busy} onClick={startCreate} type="button">
          {copy.add}
        </button>
      </header>

      <section className="nf-pantry-summary" aria-label={locale === "pt-PT" ? "Resumo da despensa" : "Pantry summary"}>
        <div><Icon name="pantry"/><small>{locale === "pt-PT" ? "Lotes disponíveis" : "Available lots"}</small><strong>{lots.filter(lot=>lot.is_available).length}</strong></div>
        <div><Icon name="calendar"/><small>{locale === "pt-PT" ? "Validade a rever" : "Expiry to review"}</small><strong>{attention}</strong></div>
        <div><Icon name="leaf"/><small>{locale === "pt-PT" ? "Sem validade registada" : "No expiry recorded"}</small><strong>{undated}</strong></div>
        <div><Icon name="book"/><small>{locale === "pt-PT" ? "Lotes registados" : "Recorded lots"}</small><strong>{lots.length}</strong></div>
      </section>
      <section className="nf-pantry-overview"><Icon name="pantry"/><div><strong>{locale === "pt-PT" ? "O que temos em casa" : "What we have at home"}</strong><p>{busy && lots.length===0 ? (locale === "pt-PT" ? "A carregar o stock registado…" : "Loading recorded stock…") : <>{lots.filter(lot=>lot.is_available).length} {locale === "pt-PT" ? "lotes ativos" : "active lots"} · {attention} {locale === "pt-PT" ? "com data próxima ou ultrapassada" : "near or past expiry"} · {undated} {locale === "pt-PT" ? "sem validade registada" : "without recorded expiry"}</>}</p></div></section>
      <div className="nf-list-controls"><label className="field"><span>{locale === "pt-PT" ? "Procurar na despensa" : "Search pantry"}</span><input type="search" value={query} onChange={event=>setQuery(event.target.value)} placeholder={locale === "pt-PT" ? "Ingrediente ou local…" : "Ingredient or location…"}/></label><nav className="nf-filter-tabs" aria-label={locale === "pt-PT" ? "Filtrar despensa" : "Filter pantry"}>{(["all","soon","undated"] as const).map(value=><button key={value} type="button" aria-pressed={filter===value} onClick={()=>setFilter(value)}>{(locale === "pt-PT" ? {all:"Todos",soon:"Rever validade",undated:"Sem data"} : {all:"All",soon:"Review expiry",undated:"Undated"})[value]}</button>)}</nav></div>
      <label className="pantry-toggle">
        <input
          checked={includeInactive}
          onChange={(event) => setIncludeInactive(event.target.checked)}
          type="checkbox"
        />
        <span>{copy.showInactive}</span>
      </label>

      {error ? <div className="error-banner" role="alert">{error}</div> : null}
      {busy && lots.length === 0 ? <div className="shell-loading">{copy.loading}</div> : null}

      {showForm ? (
        <ContextDrawer
          title={editing ? copy.edit + " · " + editing.food_item_name : copy.add}
          closeLabel={locale === "pt-PT" ? "Fechar detalhe" : "Close detail"}
          wide
          onRequestClose={closeForm}
        >
        <form className="house-editor-card pantry-editor" onSubmit={save}>
          {draftDirty ? <p className="nf-draft-state" role="status">{locale === "pt-PT" ? "Alterações por guardar" : "Unsaved changes"}</p> : null}
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
            <button className="button ghost" onClick={closeForm} type="button">
              {copy.cancel}
            </button>
          </div>
        </form>
        </ContextDrawer>
      ) : null}

      <div className="nf-pantry-columns"><div className="pantry-list">
        {!busy && shown.length === 0 ? lots.length ? <p className="empty-card" role="status">{locale === "pt-PT" ? "Sem lotes para esta pesquisa ou filtro." : "No lots match this search or filter."}</p> : <EmptyState title={copy.empty} description={locale === "pt-PT" ? "Começa pelos ingredientes que já tens em casa, com quantidade, local e validade quando conhecida. O plano desconta o stock utilizável nas compras." : "Start with ingredients at home, their quantity, location and expiry when known. Shopping deducts usable stock."}><button type="button" className="button primary" onClick={startCreate}>{copy.add}</button></EmptyState> : null}
        {shown.map((lot) => (
          <article className={`pantry-row ${lot.is_available ? "" : "inactive"}`} data-stock-state={pantryState(lot,now)} key={lot.id}>
            <div className="nf-pantry-item-main">
              <div className="nf-pantry-item-heading">
                <span className="nf-pantry-item-icon"><Icon name="pantry"/></span>
                <strong>{lot.food_item_name}</strong>
              </div>
              <div className="nf-pantry-item-quantity">
                <strong>{new Intl.NumberFormat(locale,{maximumFractionDigits:6}).format(Number(lot.quantity_available))}</strong>
                <span>{lot.unit}</span>
              </div>
              <small className="nf-expiry-badge">{(locale === "pt-PT" ? {available:"Data registada",soon:"Data nos próximos 3 dias",expired:"Data ultrapassada · rever",undated:"Sem validade registada",inactive:"Inativo",empty:"Sem quantidade disponível"} : {available:"Date recorded",soon:"Date in the next 3 days",expired:"Past recorded date · review",undated:"No recorded expiry",inactive:"Inactive",empty:"No available quantity"})[pantryState(lot,now)]}</small>
              {lot.location && <small className="nf-pantry-item-location">{locale === "pt-PT" ? "Local" : "Location"}: {lot.location}</small>}
              {lot.expires_at && <small className="nf-pantry-item-location">{copy.expires}: {lot.expires_at.slice(0, 10)}</small>}
            </div>
            <div className="row-actions">
              {!lot.is_available ? <span className="status-chip">{copy.inactive}</span> : null}
              <button className="button ghost small" disabled={busy} onClick={() => startEdit(lot)} type="button">
                {copy.edit}
              </button>
              <button
                className="button ghost small"
                disabled={busy}
                onClick={() => void changeAvailability(lot)}
                type="button"
              >
                {lot.is_available ? copy.deactivate : copy.reactivate}
              </button>
            </div>
          </article>
        ))}
      </div>
      <aside className="nf-pantry-insights" aria-label={locale === "pt-PT" ? "Análise da despensa" : "Pantry insights"}>
        <section className="nf-pantry-insights-card">
          <h2><Icon name="spark"/>{locale === "pt-PT" ? "Estado do stock" : "Stock overview"}</h2>
          <p>{locale === "pt-PT" ? "Resumo calculado apenas a partir dos lotes registados." : "Summary calculated only from recorded lots."}</p>
          <dl>
            <div><dt>{locale === "pt-PT" ? "Lotes disponíveis" : "Available lots"}</dt><dd>{lots.filter(lot=>lot.is_available).length}</dd></div>
            <div><dt>{locale === "pt-PT" ? "Validade a rever" : "Review expiry"}</dt><dd>{attention}</dd></div>
            <div><dt>{locale === "pt-PT" ? "Sem validade" : "No expiry date"}</dt><dd>{undated}</dd></div>
          </dl>
          {attention > 0 && <button className="button ghost small" type="button" onClick={()=>setFilter("soon")}>{locale === "pt-PT" ? "Rever validades" : "Review expiry"}<Icon name="arrow"/></button>}
        </section>
        <section className="nf-pantry-insights-card">
          <h2><Icon name="pantry"/>{locale === "pt-PT" ? "Gerir a despensa" : "Manage pantry"}</h2>
          <p>{locale === "pt-PT" ? "Regista quantidades, locais e prazos. As necessidades de compra exigem um limiar de reposição configurado." : "Record quantities, storage locations and expiry. Replenishment needs require a configured threshold."}</p>
          <button type="button" className="button primary" disabled={busy} onClick={startCreate}><Icon name="pantry"/>{copy.add}</button>
        </section>
      </aside></div>
    </div>
  );
}
