import { useEffect, useRef, useState } from "react";
import { registerNavigationBlocker } from "./navigation";
import {
  conditionHistory, listConditions, saveCondition,
  type ConditionEvent, type ConditionInput, type HealthCondition,
} from "./api/dietaryReviewClient";
import { useI18n } from "./i18n";
import { conditionEvidenceSummary } from "./conditionEvidence";
import "./dietary-review.css";

const empty: ConditionInput = {
  code: "", name: "", status: "reported", source: "user", source_reference: null,
  started_on: null, ended_on: null, notes: null,
};
/** Detect actual form edits, without treating opening an unchanged form as a draft. */
export function conditionDraftChanged(initial: ConditionInput, current: ConditionInput): boolean {
  return JSON.stringify(initial) !== JSON.stringify(current);
}

export default function PersonHealthConditions({familyId, personId}: {familyId: string; personId: string}) {
  const {locale} = useI18n(); const pt = locale === "pt-PT";
  const [rows, setRows] = useState<HealthCondition[]>([]);
  const [input, setInput] = useState<ConditionInput>(empty);
  const [initialInput, setInitialInput] = useState<ConditionInput>(empty);
  const [editing, setEditing] = useState<HealthCondition>();
  const [formOpen, setFormOpen] = useState(false);
  const [history, setHistory] = useState<{id: string; rows: ConditionEvent[]} | null>(null);
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true); const [revision, setRevision] = useState(0);
  const formDirty = formOpen && conditionDraftChanged(initialInput, input);
  const dirtyRef = useRef(formDirty);
  dirtyRef.current = formDirty;
  useEffect(() => {
    const release = registerNavigationBlocker(() => !dirtyRef.current || window.confirm(
      locale === "pt-PT"
        ? "Tens alterações nesta condição por guardar. Sair e descartá-las?"
        : "You have unsaved changes to this condition. Leave and discard them?",
    ));
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!dirtyRef.current) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => {
      release();
      window.removeEventListener("beforeunload", onBeforeUnload);
    };
  }, [locale]);
  function openForm(value: ConditionInput, row?: HealthCondition) {
    if (formDirty && !window.confirm(pt
      ? "Descartar alterações nesta condição?"
      : "Discard changes to this condition?")) return;
    setInitialInput(value);
    setInput(value);
    setEditing(row);
    setFormOpen(true);
  }
  function closeForm() {
    if (formDirty && !window.confirm(pt
      ? "Descartar alterações nesta condição?"
      : "Discard changes to this condition?")) return;
    setFormOpen(false);
    setEditing(undefined);
    setInput(empty);
    setInitialInput(empty);
  }
  const statuses = pt ? {reported: "Comunicada", suspected: "Suspeita", confirmed: "Confirmada por profissional", resolved: "Resolvida"}
    : {reported: "Reported", suspected: "Suspected", confirmed: "Professionally confirmed", resolved: "Resolved"};
  const sources = pt ? {user: "Utilizador", doctor: "Médico", nutritionist: "Nutricionista", document: "Documento"}
    : {user: "User", doctor: "Doctor", nutritionist: "Dietitian", document: "Document"};
  useEffect(() => {
    let cancelled = false; setLoading(true); setError("");
    void listConditions(familyId, personId).then(data => {if (!cancelled) setRows(data);})
      .catch(e => {if (!cancelled) setError(String(e));})
      .finally(() => {if (!cancelled) setLoading(false);});
    return () => {cancelled = true;};
  }, [familyId, personId, revision]);
  const change = <K extends keyof ConditionInput>(key: K, value: ConditionInput[K]) => setInput(old => ({...old, [key]: value}));
  return <section className="dietary-review" aria-busy={loading || busy}>
    <header><h2>{pt ? "Doenças e condições de saúde" : "Diseases and health conditions"}</h2>
      <p>{pt ? "Histórico individual com origem, datas e revisões. O registo de uma condição não ativa uma dieta nem altera receitas." : "Individual history with source, dates and revisions. Recording a condition does not activate a diet or change recipes."}</p>
      <p className="dietary-help">{pt ? "A origem e o estado são informações registadas, não uma verificação clínica automática. As restrições alimentares exigem orientação específica." : "Source and status are recorded information, not automatic clinical verification. Dietary restrictions require specific guidance."}</p>
      <button type="button" disabled={busy} onClick={() => openForm(empty)}>{pt ? "Adicionar condição" : "Add condition"}</button></header>
    {error && <p role="alert">{error} <button type="button" onClick={() => setRevision(x => x + 1)}>{pt ? "Recarregar" : "Reload"}</button></p>}
    {loading ? <p role="status">{pt ? "A carregar…" : "Loading…"}</p> : !rows.length && !error ? <p>{pt ? "Sem condições registadas." : "No conditions recorded."}</p> : null}
    {formOpen && <form className="dietary-form nf-condition-form" onSubmit={e => {
      e.preventDefault(); setBusy(true); setError("");
      void saveCondition(familyId, personId, input, editing).then(() => {
        setFormOpen(false); setEditing(undefined); setInput(empty); setInitialInput(empty); setHistory(null); setRevision(x => x + 1);
      }).catch(e => setError(String(e))).finally(() => setBusy(false));
    }}>
      <label>{pt ? "Nome da condição" : "Condition name"}<input required maxLength={160} value={input.name} onChange={e => change("name", e.target.value)} /></label>
      <label>{pt ? "Código estável (ex.: sibo)" : "Stable code (e.g. sibo)"}<input required disabled={!!editing} maxLength={80} pattern="[a-zA-Z0-9][a-zA-Z0-9_.-]*" value={input.code} onChange={e => change("code", e.target.value)} /></label>
      <label>{pt ? "Estado" : "Status"}<select value={input.status} onChange={e => change("status", e.target.value as HealthCondition["status"])}>{Object.entries(statuses).map(([key,label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <label>{pt ? "Origem" : "Source"}<select value={input.source} onChange={e => change("source", e.target.value as HealthCondition["source"])}>{Object.entries(sources).map(([key,label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <label>{pt ? "Referência da origem / profissional" : "Source / professional reference"}<input required={input.source !== "user"} maxLength={500} value={input.source_reference ?? ""} onChange={e => change("source_reference", e.target.value || null)} /></label>
      <label>{pt ? "Início conhecido (opcional)" : "Known start (optional)"}<input type="date" value={input.started_on ?? ""} onChange={e => change("started_on", e.target.value || null)} /></label>
      <label>{pt ? "Fim conhecido (opcional)" : "Known end (optional)"}<input type="date" min={input.started_on ?? undefined} value={input.ended_on ?? ""} onChange={e => change("ended_on", e.target.value || null)} /></label>
      <label className="dietary-wide">{pt ? "Notas e orientação recebida" : "Notes and received guidance"}<textarea maxLength={5000} value={input.notes ?? ""} onChange={e => change("notes", e.target.value || null)} /></label>
      <div className="dietary-actions"><button type="submit" disabled={busy}>{pt ? "Guardar revisão" : "Save revision"}</button><button type="button" disabled={busy} onClick={closeForm}>{pt ? "Cancelar" : "Cancel"}</button>{formDirty && <span role="status" className="nf-condition-draft-state">{pt ? "Alterações por guardar" : "Unsaved changes"}</span>}</div>
    </form>}
    {rows.map(row => <article className="dietary-card" key={row.id}>
      <h3>{row.name} <span className="dietary-badge">{statuses[row.status]}</span></h3>
      <p>{sources[row.source]}{row.source_reference ? ` · ${row.source_reference}` : ""} · {pt ? "Revisão" : "Revision"} {row.version}</p>
      <dl className="nf-condition-evidence">
        <div><dt>{pt ? "Referência da origem" : "Source reference"}</dt><dd>{conditionEvidenceSummary(row).hasSourceReference ? row.source_reference : (pt ? "Não indicada" : "Not provided")}</dd></div>
        <div><dt>{pt ? "Início conhecido" : "Known start"}</dt><dd>{row.started_on ?? (pt ? "Desconhecido" : "Unknown")}</dd></div>
        <div><dt>{pt ? "Fim conhecido" : "Known end"}</dt><dd>{row.ended_on ?? (pt ? "Desconhecido" : "Unknown")}</dd></div>
      </dl>
      {conditionEvidenceSummary(row).needsProfessionalEvidence ? (
        <p className="dietary-help" role="note">{pt ? "Confirmação profissional indicada no registo, mas a origem ou a referência apresentada não permite verificá-la aqui." : "Professional confirmation is recorded, but the listed source or reference cannot verify it here."}</p>
      ) : null}
      {row.notes && <p className="dietary-notes">{row.notes}</p>}
      <div className="dietary-actions">
        <button type="button" disabled={busy} onClick={() => openForm({code: row.code, name: row.name, status: row.status, source: row.source, source_reference: row.source_reference, started_on: row.started_on, ended_on: row.ended_on, notes: row.notes}, row)}>{pt ? "Editar / atualizar estado" : "Edit / update status"}</button>
        <button type="button" disabled={busy} onClick={() => {
          if (history?.id === row.id) {setHistory(null); return;}
          setBusy(true); setError(""); void conditionHistory(familyId, personId, row.id)
            .then(data => setHistory({id: row.id, rows: data})).catch(e => setError(String(e))).finally(() => setBusy(false));
        }}>{pt ? "Ver histórico" : "View history"}</button>
      </div>
      {history?.id === row.id && <ol>{history.rows.map(event => <li key={event.version}>
        <strong>{pt ? "Revisão" : "Revision"} {event.version}</strong> · {new Intl.DateTimeFormat(locale, {dateStyle: "medium", timeStyle: "short"}).format(new Date(event.created_at))}
        <p>{event.snapshot.name} · {statuses[event.snapshot.status]} · {sources[event.snapshot.source]}</p>
        <p>{event.snapshot.source_reference} {event.snapshot.started_on} {event.snapshot.ended_on}</p>
        <p className="dietary-notes">{event.snapshot.notes}</p>
      </li>)}</ol>}
    </article>)}
  </section>;
}
