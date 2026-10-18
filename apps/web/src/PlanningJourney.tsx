import { useEffect, useRef, useState } from "react";
import { listFamilyPersons } from "./api/client";
import { listRecipeReviews, type ReviewRecipe } from "./api/dietaryReviewClient";
import { getWeekSetup, getPlanningRestrictions, listRetailAlternatives, saveWeekSetup, type PlanningRestrictions, type RetailAlternative, type WeekSetup } from "./api/planningWorkspaceClient";
import type { MealType } from "./api/mealPlanTypes";
import type { Person } from "./api/types";
import { useI18n } from "./i18n";
import WeeklyProposalPreview from "./WeeklyProposalPreview";
import ShoppingListScreen from "./ShoppingListScreen";
import SelectedMealOptions from "./SelectedMealOptions";
import RetailAlternativeCards from "./RetailAlternativeCards";
import {adaptationSummaries} from "./RecipeAdaptationCards";
import "./planning-journey.css";
import {copyWeeklyOrganisation, repeatMealAttendance} from "./weeklyAttendance";
import {calendarDateOffset} from "./mealAlternatives";

export function nextWeekMonday(referenceDate: string): string {
  const date = new Date(`${referenceDate}T12:00:00Z`);
  if (Number.isNaN(date.getTime())) throw new Error("Invalid reference date");
  const days = (8 - date.getUTCDay()) % 7 || 7;
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}
export function exclusionGroups(recipes: ReviewRecipe[]) {
  const groups = new Map<string, {namePt: string; nameEn: string; ids: Set<string>}>();
  for (const r of recipes) for (const i of r.ingredients) for (const ref of i.references) {
    if (ref.classification !== "high") continue;
    const group = groups.get(ref.reference_key) ?? {namePt: ref.name_pt, nameEn: ref.name_en, ids: new Set<string>()};
    group.ids.add(i.food_item_id); groups.set(ref.reference_key, group);
  }
  return [...groups.entries()].map(([key,g]) => ({key, namePt:g.namePt, nameEn:g.nameEn, ids:[...g.ids]}));
}
export function exclusionsForMeal(manual: string[], rules: PlanningRestrictions, day: string, meal: MealType, attendees: string[]): string[] {
  return [...new Set([...manual,...rules.sources.filter(s=>attendees.includes(s.person_id) && s.dates.includes(day) && s.meal_types.includes(meal)).flatMap(s=>s.food_item_ids)])];
}
const meals: MealType[] = ["breakfast", "lunch", "snack", "dinner"];
export default function PlanningJourney({familyId, referenceDate, onPlanChanged, onOpenAgenda}: {
  familyId: string; referenceDate: string; onPlanChanged?: () => void; onOpenAgenda: (week?:string) => void;
}) {
  const {locale} = useI18n(); const pt = locale === "pt-PT";
  const [week, setWeek] = useState(() => nextWeekMonday(referenceDate));
  const [people, setPeople] = useState<Person[]>([]); const [recipes, setRecipes] = useState<ReviewRecipe[]>([]);
  const [products, setProducts] = useState<RetailAlternative[]>([]);
  const [setup, setSetup] = useState<WeekSetup>({week_start:week, version:0, person_ids:[], meal_types:["dinner"], excluded_food_item_ids:[]});
  const choiceRevision=useRef(0);
  const copyRequest=useRef(0);
  const [copyBusy,setCopyBusy]=useState(false);
  const [organisationNotice,setOrganisationNotice]=useState("");
  const [step, setStep] = useState(1); const [error, setError] = useState("");
  const [busy, setBusy] = useState(true); const [loadedWeek, setLoadedWeek] = useState("");
  const [applied, setApplied] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [loadRevision, setLoadRevision] = useState(0);
  const [shoppingWarning, setShoppingWarning] = useState(false);
  const [retailWarning, setRetailWarning] = useState(false);
  const [automatic, setAutomatic] = useState<PlanningRestrictions>({excluded_food_item_ids:[],sources:[],warnings:[]});
  const [rulesBusy, setRulesBusy] = useState(true);
  const [rulesError, setRulesError] = useState("");
  const mealLabels = pt ? {breakfast:"Pequeno-almoço",lunch:"Almoço",snack:"Lanche",dinner:"Jantar"} : {breakfast:"Breakfast",lunch:"Lunch",snack:"Snack",dinner:"Dinner"};
  useEffect(() => {
    choiceRevision.current++; copyRequest.current++; setCopyBusy(false); setOrganisationNotice("");
    let cancelled = false; setBusy(true); setError(""); setLoadedWeek(""); setRetailWarning(false);
    void Promise.all([listFamilyPersons(familyId), listRecipeReviews(familyId), getWeekSetup(familyId,week), listRetailAlternatives(familyId).catch(() => {if (!cancelled) setRetailWarning(true);return [];})])
      .then(([persons,catalogue,saved,retail]) => {
        if (cancelled) return;
        setPeople(persons); setRecipes(catalogue); setProducts(retail);
        setSetup(saved ?? {week_start:week,version:0,person_ids:persons.map(p => p.id),meal_types:["dinner"],excluded_food_item_ids:[]});
        setLoadedWeek(week);
      }).catch(e => {if (!cancelled) setError(String(e));}).finally(() => {if (!cancelled) setBusy(false);});
    return () => {cancelled=true;choiceRevision.current++;copyRequest.current++;};
  }, [familyId,week,loadRevision]);
  const peopleKey=setup.person_ids.join(","); const mealsKey=setup.meal_types.join(",");
  useEffect(()=>{
    let cancelled=false;
    setRulesBusy(true); setRulesError(""); setAutomatic({excluded_food_item_ids:[],sources:[],warnings:[]}); setConfirmed(false);
    if (loadedWeek!==week || !setup.person_ids.length || !setup.meal_types.length) return;
    void getPlanningRestrictions(familyId,{...setup,week_start:week}).then(result=>{
      if (!cancelled) setAutomatic(result);
    }).catch(e=>{if(!cancelled) setRulesError(String(e));}).finally(()=>{if(!cancelled) setRulesBusy(false);});
    return ()=>{cancelled=true;};
    // Manual exclusions do not change the source rules.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[familyId,week,loadedWeek,peopleKey,mealsKey,JSON.stringify(setup.attendance ?? []),loadRevision]);
  const invalidAttendance = (setup.attendance ?? []).some(a=>a.person_ids.length===1);
  const selectedPeople = people.filter(p => setup.person_ids.includes(p.id));
  const effectiveExcluded=[...new Set([...automatic.excluded_food_item_ids,...setup.excluded_food_item_ids])];
  const groups = exclusionGroups(recipes);
  function changeChoices(update: (previous: WeekSetup) => WeekSetup) {
    choiceRevision.current++;
    setSetup(previous => {
      const next = update(previous);
      return {...next, attendance: (next.attendance ?? []).filter(a=>next.meal_types.includes(a.meal_type)).map(a=>({...a,person_ids:a.person_ids.filter(id=>next.person_ids.includes(id))}))};
    }); setConfirmed(false); setApplied(false);
  }
  async function copyPreviousWeek() {
    const request=++choiceRevision.current;
    const copyId=++copyRequest.current;
    setCopyBusy(true);setError("");setOrganisationNotice("");
    try {
      const source=await getWeekSetup(familyId,calendarDateOffset(week,-7));
      if(request!==choiceRevision.current)return;
      if(!source){setOrganisationNotice(pt?"A semana anterior ainda não tem uma organização guardada.":"The previous week has no saved organisation yet.");return;}
      const copied=copyWeeklyOrganisation(source,setup,people.map(p=>p.id));
      changeChoices(()=>copied);
      setOrganisationNotice(pt?"Presenças e origens copiadas. Revê as restrições recalculadas antes de gerar; não foram copiadas refeições.":"Attendance and sources copied. Review recalculated restrictions before generating; meals were not copied.");
    } catch(e) {
      if(request===choiceRevision.current)setError(e instanceof Error && e.message==="unavailable_attendee" ? (pt?"Há uma pessoa da semana anterior que já não está disponível. Escolhe os presentes manualmente.":"A previous attendee is unavailable. Select attendance manually.") : String(e));
    } finally {if(copyId===copyRequest.current)setCopyBusy(false);}
  }
  const labels = pt ? ["Semana e pessoas", "Restrições", "Rever refeições", "Compras"] : ["Week and people", "Restrictions", "Review meals", "Shopping"];
  async function proceed() {
    setBusy(true); setError("");
    try {const saved = await saveWeekSetup(familyId,setup); setSetup(saved); setStep(3); setApplied(false);}
    catch(e) {setError(String(e));} finally {setBusy(false);}
  }
  return <div className="planning-journey">
    <header className="screen-header"><div><span className="eyebrow">{pt ? "Da semana às compras" : "From the week to shopping"}</span>
      <h1>{pt ? "Vamos planear a próxima semana" : "Let's plan next week"}</h1>
      <p>{pt ? "Escolhe quem participa. As restrições vêm das dietas e condições ativas; revê as trocas nas receitas antes de guardar e passar às compras." : "Choose who joins. Restrictions come from active diets and conditions; review recipe substitutions before saving and shopping."}</p></div>
      <button type="button" className="button ghost" onClick={()=>onOpenAgenda(week)}>{pt ? "Ver agenda existente" : "View existing agenda"}</button>
    </header>
    <nav className="journey-steps" aria-label={pt ? "Etapas do planeamento" : "Planning steps"}>{labels.map((label,index) => <button type="button" key={label} aria-current={step===index+1 ? "step" : undefined} disabled={busy || (index+1>step && !(index===3 && applied))} onClick={() => {setStep(index+1);}}><b>{index+1}</b><span>{label}</span></button>)}</nav>
    {error && <p className="error-banner" role="alert">{error} <button type="button" className="button ghost" onClick={()=>setLoadRevision(v=>v+1)}>{pt ? "Recarregar escolhas" : "Reload choices"}</button></p>}
    {retailWarning && <p role="status">{pt ? "As alternativas de supermercado estão temporariamente indisponíveis; podes continuar a planear." : "Supermarket alternatives are temporarily unavailable; you can continue planning."}</p>}
    {busy && loadedWeek!==week && <p role="status">{pt ? "A preparar a tua semana…" : "Preparing your week…"}</p>}
    {step===1 && <section className="journey-card">
      <h2>{pt ? "1. Quando e quem come em casa?" : "1. When and who eats at home?"}</h2>
      <label className="field"><span>{pt ? "Semana a começar na segunda-feira" : "Week starting Monday"}</span><input type="date" min="1990-01-01" step={7} value={week} disabled={busy||copyBusy} onChange={e => {setWeek(e.target.value);setApplied(false);setConfirmed(false);}} /></label>
      <button type="button" className="button secondary" disabled={busy||copyBusy||loadedWeek!==week} onClick={()=>void copyPreviousWeek()}>{copyBusy ? pt?"A copiar…":"Copying…" : pt?"Copiar organização da semana anterior":"Copy previous week's organisation"}</button>
      {organisationNotice&&<p role="status">{organisationNotice}</p>}
      <fieldset><legend>{pt ? "Pessoas para estas refeições" : "People for these meals"}</legend>
        <p className="muted">{pt ? "Seleciona o grupo habitual e ajusta os presentes em cada refeição abaixo. Sem pessoas, essa refeição não será gerada." : "Select the usual group and adjust attendance for each meal below. Meals with nobody attending will not be generated."}</p>
        <div className="journey-checks">{people.map(p => <label key={p.id}><input type="checkbox" disabled={busy||copyBusy} checked={setup.person_ids.includes(p.id)} onChange={e => changeChoices(s => ({...s,person_ids:e.target.checked ? [...s.person_ids,p.id] : s.person_ids.filter(id=>id!==p.id)}))} />{p.first_name} {p.last_name}</label>)}</div>
      </fieldset>
      <fieldset><legend>{pt ? "Que refeições queres gerar?" : "Which meals should be generated?"}</legend><div className="journey-checks">{meals.map(m => <label key={m}><input type="checkbox" disabled={busy||copyBusy} checked={setup.meal_types.includes(m)} onChange={e => changeChoices(s => ({...s,meal_types:e.target.checked ? [...s.meal_types,m] : s.meal_types.filter(v=>v!==m)}))}/>{mealLabels[m]}</label>)}</div></fieldset>
      <fieldset><legend>{pt?"De onde vem cada refeição?":"Where does each meal come from?"}</legend>
        {setup.meal_types.map(meal=><label className="field" key={meal}><span>{mealLabels[meal]}</span><select disabled={busy||copyBusy} value={setup.meal_sources?.[meal] ?? (meal==="lunch" ? "delivery":"home")} onChange={e=>changeChoices(s=>({...s,meal_sources:{...s.meal_sources,[meal]:e.target.value as "home"|"delivery"|"restaurant"}}))}><option value="home">{pt?"Cozinhar em casa":"Cook at home"}</option><option value="delivery">{pt?"Entrega · Uber Eats / Glovo / Bolt Food":"Delivery · Uber Eats / Glovo / Bolt Food"}</option><option value="restaurant">{pt?"Restaurante":"Restaurant"}</option></select></label>)}
        <p>{pt?"Nos almoços começamos pela entrega. Sem catálogo ligado, a refeição fica por escolher: abre-a na semana para consultar as plataformas e os restaurantes.":"Lunch starts with delivery. Without a connected catalogue, the meal remains pending: open it in the week to browse platforms and restaurants."}</p>
      </fieldset>
      <details><summary>{pt ? "Quem está em cada refeição?" : "Who attends each meal?"}</summary>
        {Array.from({length:7},(_,offset)=>{const d=new Date(`${week}T12:00:00Z`);d.setUTCDate(d.getUTCDate()+offset);return d.toISOString().slice(0,10);}).flatMap(day=>setup.meal_types.map(meal=>{
          const attendees=setup.attendance?.find(a=>a.planning_date===day && a.meal_type===meal)?.person_ids ?? setup.person_ids;
          return <fieldset key={`${day}:${meal}`}><legend>{day} · {mealLabels[meal]}</legend><div className="journey-checks">{people.filter(p=>setup.person_ids.includes(p.id)).map(p=><label key={p.id}><input type="checkbox" disabled={busy||copyBusy} checked={attendees.includes(p.id)} onChange={e=>changeChoices(s=>({...s,attendance:[...(s.attendance ?? []).filter(a=>a.planning_date!==day || a.meal_type!==meal),{planning_date:day,meal_type:meal,person_ids:e.target.checked ? [...attendees,p.id] : attendees.filter(id=>id!==p.id)}]}))}/>{p.first_name}</label>)}</div><button type="button" className="button ghost small" disabled={busy||copyBusy||attendees.length===1} onClick={()=>{changeChoices(s=>repeatMealAttendance(s,meal,attendees));setOrganisationNotice(pt?"Presenças repetidas nesta refeição durante os sete dias. Podes ajustar exceções abaixo.":"Attendance repeated for this meal across all seven days. You can adjust exceptions below.");}}>{pt?"Repetir estas presenças em todos os dias":"Repeat these attendees on every day"}</button>{attendees.length===0 && <p>{pt ? "Sem refeição a gerar." : "No meal to generate."}</p>}{attendees.length===1 && <p role="alert">{pt ? "Por agora, planeia esta refeição individual na agenda ou seleciona pelo menos duas pessoas." : "For now, plan this individual meal in the agenda or select at least two people."}</p>}</fieldset>;
        }))}
      </details>
      <p>{pt ? "Começamos pelos jantares; podes incluir os outros tempos. As refeições já guardadas são preservadas." : "Start with dinners; you can include other meals. Already saved meals are preserved."}</p>
      <button type="button" className="button primary" disabled={busy || copyBusy || loadedWeek!==week || setup.person_ids.length<2 || invalidAttendance || !setup.meal_types.length} onClick={()=>setStep(2)}>{pt ? "Continuar para restrições →" : "Continue to restrictions →"}</button>
      {!busy && setup.person_ids.length<2 && <p>{pt ? "A geração partilhada precisa de pelo menos duas pessoas. Usa a agenda para refeições individuais." : "Shared generation needs at least two people. Use the agenda for individual meals."}</p>}
    </section>}
    {step===2 && <section className="journey-card">
      <h2>{pt ? "2. O que devemos evitar nestas refeições?" : "2. What should we avoid in these meals?"}</h2>
      <p>{pt ? "As restrições já vêm selecionadas a partir das condições e dietas ativas das pessoas presentes. Podes acrescentar exclusões para esta semana." : "Restrictions are preselected from active conditions and diets of the people attending. You can add exclusions for this week."}</p>
      {rulesBusy && <p role="status">{pt ? "A calcular restrições automáticas…" : "Calculating automatic restrictions…"}</p>}
      {rulesError && <p role="alert" className="error-banner">{rulesError} <button type="button" className="button ghost" onClick={()=>setLoadRevision(v=>v+1)}>{pt ? "Voltar a calcular restrições" : "Retry automatic restrictions"}</button></p>}
      {automatic.sources.map(s=><p key={s.source_id} className="journey-context"><strong>{people.find(p=>p.id===s.person_id)?.first_name}: {s.label}</strong><br/>{pt ? "Selecionado automaticamente" : "Automatically selected"} · {s.dates[0]} — {s.dates.at(-1)}</p>)}
      {automatic.warnings.map(w=><p role="status" key={w}>{w}</p>)}
      <div className="journey-checks">{groups.map(g => {
        const auto=g.ids.some(id=>automatic.excluded_food_item_ids.includes(id));
        return <label key={g.key}><input type="checkbox" disabled={auto||rulesBusy} checked={g.ids.every(id=>effectiveExcluded.includes(id))} onChange={e=>changeChoices(s=>({...s,excluded_food_item_ids:e.target.checked ? [...new Set([...s.excluded_food_item_ids,...g.ids])] : s.excluded_food_item_ids.filter(id=>!g.ids.includes(id))}))}/>{pt ? g.namePt:g.nameEn}{auto && <small> · {pt ? "automático" : "automatic"}</small>}</label>;
      })}</div>
      <p className="muted">{pt ? "As escolhas automáticas seguem os perfis configurados. O motor verifica os ingredientes registados; produtos compostos, doses e tolerância FODMAP podem continuar por confirmar." : "Automatic choices follow configured profiles. The engine checks recorded ingredients; compound products, portions and FODMAP tolerance may remain unconfirmed."}</p>
      <details><summary>{pt ? "Como passar de uma substituição a uma compra concreta" : "From a substitution to a concrete purchase"}</summary><RetailAlternativeCards familyId={familyId} products={products} /></details>
      <label className="journey-confirm"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>{pt ? "Revi as pessoas, refeições e exclusões para esta semana." : "I reviewed people, meals and exclusions for this week."}</label>
      <div className="journey-actions"><button className="button ghost" type="button" disabled={busy} onClick={()=>setStep(1)}>{pt ? "← Voltar" : "← Back"}</button><button className="button primary" type="button" disabled={busy||rulesBusy||!!rulesError||!confirmed} onClick={()=>void proceed()}>{busy ? pt ? "A guardar escolhas…":"Saving choices…" : pt ? "Guardar escolhas e gerar refeições →":"Save choices and generate meals →"}</button></div>

    </section>}
    {step===3 && <>
      <div className="journey-context"><strong>{week} · {selectedPeople.map(p=>p.first_name).join(" · ")}</strong><p>{pt ? "Revê a proposta e usa «Aplicar semana». Só depois as refeições são guardadas e a lista de compras é calculada." : "Review the proposal and choose Apply week. Only then are meals saved and shopping calculated."}</p></div>
      <WeeklyProposalPreview recipeReviews={recipes} key={`${familyId}:${week}:${setup.version}`} familyId={familyId} weekStart={week} people={selectedPeople} recipeAdaptations={adaptationSummaries(recipes,effectiveExcluded)} renderSelectedMeal={context=><SelectedMealOptions key={`${context.planningDate}:${context.mealType}:${context.recipeId}:${context.personIds.join(",")}`} familyId={familyId} context={context} recipes={recipes} products={products} restrictions={automatic} people={people} manualExclusions={setup.excluded_food_item_ids} onVariantsChanged={()=>{void listRecipeReviews(familyId).then(setRecipes).catch(e=>setError(String(e)));}}/>} recipeAdaptationsForParticipants={(day,meal,attendees)=>adaptationSummaries(recipes,exclusionsForMeal(setup.excluded_food_item_ids,automatic,day,meal,attendees))} planningOptions={{mealSources:setup.meal_sources ?? {lunch:"delivery"},mealTypes:setup.meal_types,excludedFoodItemIds:setup.excluded_food_item_ids,attendance:setup.attendance}} autoGenerate={!applied} onPlanChanged={onPlanChanged} onApplied={(updated)=>{setApplied(true);setShoppingWarning(!updated);setStep(4);}} />

    </>}
    {step===4 && <><div className="journey-context"><h2>{pt ? "Plano guardado. Vamos às compras." : "Plan saved. Time for shopping."}</h2><p>{pt ? "A lista considera as refeições guardadas e o stock da despensa. Confirma os avisos de quantidades em falta e revê as alternativas de loja." : "The list considers saved meals and pantry stock. Check missing-quantity issues and review store alternatives."}</p></div>{shoppingWarning && <p role="alert" className="error-banner">{pt ? "O plano foi guardado, mas as compras não foram atualizadas. Tenta «Atualizar» abaixo." : "The plan was saved but shopping was not refreshed. Try Refresh below."}</p>}<ShoppingListScreen familyId={familyId} initialStartDate={week}/></>}
  </div>;
}
