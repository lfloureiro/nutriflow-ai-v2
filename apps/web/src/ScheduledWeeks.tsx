import {useEffect,useState} from "react";
import {getFamilyMealPlan} from "./api/client";
import {listRecipeReviews,type ReviewRecipe} from "./api/dietaryReviewClient";
import type {FamilyMealPlan} from "./api/mealPlanTypes";
import {calendarDateOffset,calendarMonday} from "./mealAlternatives";
import SavedMealChanges from "./SavedMealChanges";
import {useI18n} from "./i18n";
export default function ScheduledWeeks({familyId,referenceDate,onOpenWeek,initialWeek}:{familyId:string;referenceDate:string;initialWeek?:string;onOpenWeek:(date:string)=>void}){
  const {locale}=useI18n();const pt=locale==="pt-PT";const [week,setWeek]=useState(calendarMonday(initialWeek??referenceDate));
  const [plan,setPlan]=useState<FamilyMealPlan|null>(null);const [recipes,setRecipes]=useState<ReviewRecipe[]>([]);
  const [busy,setBusy]=useState(true);const [error,setError]=useState("");const [alternativesError,setAlternativesError]=useState(false);
  useEffect(()=>{let cancelled=false;setRecipes([]);setAlternativesError(false);void listRecipeReviews(familyId).then(r=>{if(!cancelled)setRecipes(r);}).catch(()=>{if(!cancelled)setAlternativesError(true);});return()=>{cancelled=true;};},[familyId]);
  useEffect(()=>{let cancelled=false;setBusy(true);setError("");setPlan(null);void getFamilyMealPlan(familyId,week,7).then(r=>{if(!cancelled)setPlan(r);}).catch(e=>{if(!cancelled)setError(String(e));}).finally(()=>{if(!cancelled)setBusy(false);});return()=>{cancelled=true;};},[familyId,week]);
  const entries=plan?.days.flatMap(day=>day.slots.flatMap(slot=>slot.meals.filter(m=>m.status!=="cancelled").map(entry=>({day:day.date,meal:slot.meal_type,entry}))))??[];
  const names=pt?{breakfast:"Pequeno-almoço",lunch:"Almoço",snack:"Lanche",dinner:"Jantar"}:{breakfast:"Breakfast",lunch:"Lunch",snack:"Snack",dinner:"Dinner"};
  return <section className="journey-card home-scheduled-weeks" aria-label={pt?"Semanas e refeições agendadas":"Weeks and scheduled meals"}>
    <h2>{pt?"As nossas semanas":"Our weeks"}</h2><p>{pt?"Vê o que já está guardado e as alternativas de cada prato.":"See saved meals and the alternatives for each dish."}</p>
    <nav className="journey-actions" aria-label={pt?"Escolher semana":"Choose week"}>
      <button type="button" className="button ghost" onClick={()=>setWeek(calendarDateOffset(week,-7))}>{pt?"‹ Anterior":"‹ Previous"}</button>
      <button type="button" className="button ghost" onClick={()=>setWeek(calendarMonday(referenceDate))}>{pt?"Esta semana":"This week"}</button>
      <button type="button" className="button ghost" onClick={()=>setWeek(calendarDateOffset(calendarMonday(referenceDate),7))}>{pt?"Próxima semana":"Next week"}</button>
      <button type="button" className="button ghost" onClick={()=>setWeek(calendarDateOffset(week,7))}>{pt?"Seguinte ›":"Next ›"}</button>
    </nav>
    <label className="field"><span>{pt?"Semana a consultar":"Week to view"}</span><input type="date" value={week} onChange={e=>{if(e.target.value)setWeek(calendarMonday(e.target.value));}}/></label>
    <p><strong>{week} — {calendarDateOffset(week,6)}</strong> · {entries.length} {pt?"refeições guardadas":"saved meals"}</p>
    {busy&&<p role="status">{pt?"A carregar a semana…":"Loading the week…"}</p>}{error&&<p role="alert">{error}</p>}
    {alternativesError&&<p role="status">{pt?"Não foi possível carregar as alternativas dos ingredientes.":"Ingredient alternatives could not be loaded."}</p>}
    {!busy&&!error&&!entries.length&&<p>{pt?"Ainda não há refeições guardadas nesta semana. Uma proposta só entra na agenda depois de aplicada.":"No saved meals this week. A proposal enters the agenda once it is applied."}</p>}
    <div className="scheduled-week-meals">{entries.map(({day,meal,entry})=><button type="button" className="scheduled-meal-card" key={entry.id} onClick={()=>onOpenWeek(day)}><small>{day} · {names[meal]} · {entry.local_time.slice(0,5)}</small><strong>{entry.recipe_name??entry.title??names[meal]}</strong><SavedMealChanges entry={entry} recipes={recipes}/><small>{pt?"Abrir na agenda →":"Open in agenda →"}</small></button>)}</div>
    <button type="button" className="button primary" onClick={()=>onOpenWeek(week)}>{pt?"Abrir esta semana na agenda":"Open this week in the agenda"}</button>
  </section>;
}
