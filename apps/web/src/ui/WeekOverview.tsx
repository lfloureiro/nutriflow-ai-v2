import type {FamilyMealPlan} from "../api/mealPlanTypes";
import {useI18n} from "../i18n";

export function weekOverview(plan: FamilyMealPlan) {
  let occupied=0,events=0,adapted=0,total=0;
  for(const day of plan.days)for(const slot of day.slots){
    total++;
    const meals=slot.meals.filter(meal=>meal.status!=="cancelled");
    events+=meals.length;
    if(meals.length)occupied++;
    if(meals.some(meal=>meal.transformations.length || meal.variant_changes?.length))adapted++;
  }
  return {occupied,events,adapted,total,empty:total-occupied};
}
export default function WeekOverview({plan,proposed=0}:{plan:FamilyMealPlan;proposed?:number}) {
  const {locale}=useI18n();const pt=locale==="pt-PT";const summary=weekOverview(plan);
  const date=(value:string)=>new Intl.DateTimeFormat(locale,{day:"numeric",month:"short",timeZone:"UTC"}).format(new Date(value+"T12:00:00Z"));
  return <section className="nf-week-overview" aria-label={pt?"Resumo da semana":"Week overview"}>
    <div><span className="eyebrow">{pt?"A NOSSA SEMANA":"OUR WEEK"}</span><h3>{date(plan.start_date)} — {date(plan.end_date)}</h3><p>{pt?"Uma visão clara do que já está decidido e do que falta escolher.":"See what is decided and what still needs a choice."}</p></div>
    <div className="nf-week-counts"><span><b>{summary.occupied}/{summary.total}</b>{pt?"tempos planeados":"planned slots"}</span><span><b>{summary.empty}</b>{pt?"por preencher":"to fill"}</span>{proposed>0&&<span className="is-proposed"><b>{proposed}</b>{pt?"em proposta":"proposed"}</span>}{summary.adapted>0&&<span><b>{summary.adapted}</b>{pt?"com adaptação aplicada":"with applied adaptations"}</span>}</div>
    <progress max={Math.max(1,summary.total)} value={summary.occupied} aria-label={pt?"Tempos de refeição guardados":"Saved meal slots"}/>
    <small>{pt?"Planeada indica que está guardada. A adequação é verificada por pessoa e porção no detalhe.":"Planned means saved. Suitability is checked per person and portion in the detail."}</small>
  </section>;
}
