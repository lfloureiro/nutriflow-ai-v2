import {updatePerson} from "../api/setupClient";
import {useState} from "react";
import {useI18n} from "../i18n";
import PersonAvatar from "./PersonAvatar";
import {type AvatarPreference, type AvatarStage, type AvatarStyle} from "./avatarPreferences";

export default function AvatarAppearanceEditor({familyId, personId, name, age, sex, appearance, onSaved}: {familyId:string;personId:string;name:string;age?:number|null;sex?:"male"|"female"|null;appearance?:AvatarPreference|null;onSaved:()=>void}) {
  const {locale} = useI18n();const pt = locale === "pt-PT";
  const saved = appearance ?? {};
  const [busy,setBusy] = useState(false);
  const [draft,setDraft] = useState<AvatarPreference>(saved);
  const [status,setStatus] = useState("");
  const stages: [AvatarStage,string,string][] = [["child","Criança","Child"],["teen","Adolescente","Teen"],["young","Adulto jovem · 18–29","Young adult · 18–29"],["adult","Adulto · 30–44","Adult · 30–44"],["mature","Meia-idade · 45–64","Middle age · 45–64"],["senior","Sénior · 65+","Senior · 65+"]];
  async function save(preference: AvatarPreference) {
    setBusy(true);
    try {await updatePerson(personId,{avatar_appearance:Object.keys(preference).length ? preference : null});onSaved();setDraft(preference);setStatus(pt ? "Avatar guardado no perfil." : "Avatar saved to profile.");}
    catch {setStatus(pt ? "Não foi possível guardar o avatar." : "Could not save this avatar.");} finally {setBusy(false);}
  }
  return <details className="nf-avatar-editor"><summary>{pt ? "Personalizar avatar" : "Customize avatar"}</summary>
    <p className="muted">{pt ? "Aparência visual guardada para esta pessoa. Não altera a idade, o sexo ou os cálculos do perfil." : "Visual appearance saved for this person. Does not change age, sex or profile calculations."}</p>
    <div className="nf-avatar-editor-body"><PersonAvatar identity={personId} familyIdentity={familyId} name={name} age={age} sex={sex} size="lg" preview={draft}/><div className="form-grid two">
      <label className="field"><span>{pt ? "Geração" : "Generation"}</span><select value={draft.stage ?? "auto"} onChange={event=>{const {stage:_,...rest}=draft;setDraft(event.target.value === "auto" ? rest : {...draft,stage:event.target.value as AvatarStage});setStatus("");}}><option value="auto">{pt ? "Usar idade do perfil" : "Use profile age"}</option>{stages.map(([value,ptLabel,enLabel])=><option key={value} value={value}>{pt ? ptLabel : enLabel}</option>)}</select></label>
      <label className="field"><span>{pt ? "Apresentação" : "Presentation"}</span><select value={draft.style ?? "auto"} onChange={event=>{const {style:_,...rest}=draft;setDraft(event.target.value === "auto" ? rest : {...draft,style:event.target.value as AvatarStyle});setStatus("");}}><option value="auto">{pt ? "Usar perfil" : "Use profile"}</option><option value="male">{pt ? "Masculina" : "Masculine"}</option><option value="female">{pt ? "Feminina" : "Feminine"}</option><option value="neutral">{pt ? "Neutra" : "Neutral"}</option></select></label>
    </div></div>
    <fieldset className="nf-avatar-variants"><legend>{pt ? "Escolhe um estilo" : "Choose a style"}</legend>{[0,1,2,3,4,5].map(variant=><button key={variant} type="button" aria-label={`${pt ? "Estilo" : "Style"} ${variant+1}`} aria-pressed={draft.variant === variant} onClick={()=>{setDraft({...draft,variant});setStatus("");}}><PersonAvatar identity={personId} familyIdentity={familyId} name={name} age={age} sex={sex} preview={{...draft,variant}} decorative/></button>)}</fieldset>
    <div className="button-row"><button type="button" className="button primary" disabled={busy} onClick={()=>void save(draft)}>{pt ? "Guardar avatar" : "Save avatar"}</button><button type="button" className="button ghost" disabled={busy} onClick={()=>void save({})}>{pt ? "Usar dados do perfil" : "Use profile data"}</button></div><p role="status">{status}</p>
  </details>;
}
