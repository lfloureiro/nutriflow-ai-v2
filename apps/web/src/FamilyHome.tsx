import {useEffect, useState} from "react";
import ScheduledWeeks from "./ScheduledWeeks";
import {calendarDateOffset,calendarMonday} from "./mealAlternatives";
import type {FamilyDashboard, FamilyDashboardMeal, FamilyDashboardMember} from "./api/types";
import {useI18n, type Locale} from "./i18n";
import Icon from "./ui/Icon";
import {resolveMealHeroImage} from "./mealHeroImages";
import PersonAvatar from "./ui/PersonAvatar";
import {EmptyState, Panel} from "./ui/primitives";
import "./planning-journey.css";
import "./home-v3.css";

export function memberDisplayName(member: FamilyDashboardMember): string {
  return [member.first_name, member.last_name].filter(Boolean).join(" ");
}
/** A dashboard reports consumption and planned energy, not a medical target.
 * Never equate zero consumption or a planning estimate to an achieved goal. */
export function familyNutritionSummary(members: FamilyDashboardMember[]) {
  const valid = (value: string | null | undefined) => {
    if (value == null || value.trim() === "") return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
  };
  return members.map(member => {
    const consumed = valid(member.nutrition?.energy_consumed_kcal);
    const planned = valid(member.nutrition?.energy_planned_kcal);
    const hasConfirmedConsumption = consumed !== null && consumed > 0;
    return {
      member, consumed, planned,
      hasConfirmedConsumption,
      ratio: hasConfirmedConsumption && planned !== null && planned > 0
        ? Math.min(100, Math.round(100 * consumed / planned)) : null,
    };
  });
}
export function formatMealTime(scheduledAt: string, timezone: string, locale: Locale): string {
  return new Intl.DateTimeFormat(locale, {hour: "2-digit", minute: "2-digit", timeZone: timezone}).format(new Date(scheduledAt));
}
function localClock(now: number, timezone: string) {
  const parts = new Intl.DateTimeFormat("en-GB", {timeZone:timezone,year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",hourCycle:"h23"}).formatToParts(new Date(now));
  const part = (type:string) => parts.find(item=>item.type===type)?.value ?? "";
  return {date:`${part("year")}-${part("month")}-${part("day")}`,hour:Number(part("hour"))};
}
export function currentMealKind(now: number, timezone: string): string {
  const {hour} = localClock(now,timezone);
  return hour < 11 ? "breakfast" : hour < 15 ? "lunch" : hour < 18 ? "snack" : "dinner";
}
export function nextFamilyMeal(meals: FamilyDashboardMeal[], now = Date.now(), timezone = "Europe/Lisbon"): FamilyDashboardMeal | undefined {
  const pending = meals.filter(meal => !["cancelled", "completed"].includes(meal.status) && Number.isFinite(Date.parse(meal.scheduled_at)))
    .sort((a,b) => Date.parse(a.scheduled_at) - Date.parse(b.scheduled_at));
  const today = localClock(now,timezone).date;
  const kind = currentMealKind(now,timezone);
  // An unfinished dinner is still relevant after its scheduled time; an old snack is not.
  const current = pending.filter(meal => meal.meal_type === kind && Date.parse(meal.scheduled_at) <= now && localClock(Date.parse(meal.scheduled_at),timezone).date === today).at(-1);
  return current ?? pending.find(meal => Date.parse(meal.scheduled_at) >= now);
}
/** A photographed card is only shown when the actual meal name has a verified match. */
function TodayMealPhoto({title}:{title:string|null}) {
  const match=title ? resolveMealHeroImage({planned:{title}}) : null;
  const [failed,setFailed]=useState<string|null>(null);
  return match && match.src!==failed ?
    <img className="nf-today-photo" src={match.src} alt="" loading="lazy"
      referrerPolicy="no-referrer" onError={()=>setFailed(match.src)} /> :
    <span className="nf-today-photo-fallback" aria-hidden="true"><Icon name="cloche"/></span>;
}

export default function FamilyHome({dashboard, onPlanMeal, onOpenPerson, onOpenWeek, weekDate, onOpenRecipes, onOpenShopping, onAdaptPlan}: {
  dashboard: FamilyDashboard; onPlanMeal: () => void; onOpenPerson: (personId: string) => void;
  onOpenWeek?: (date: string) => void; weekDate?: string; onOpenRecipes?:()=>void;onOpenShopping?:()=>void; onAdaptPlan?:()=>void;
}) {
  const {locale, t} = useI18n();
  const pt = locale === "pt-PT";
  const [now,setNow] = useState(()=>Date.now());
  useEffect(()=>{const timer=window.setInterval(()=>setNow(Date.now()),30_000);return ()=>window.clearInterval(timer);},[]);
  const next = nextFamilyMeal(dashboard.meals,now,dashboard.timezone);
  const nextImage = next ? resolveMealHeroImage({planned: {title: next.title}}) : null;
  const [failedHomeImage,setFailedHomeImage] = useState<string | null>(null);
  const shownHomeImage = nextImage && failedHomeImage !== nextImage.src ? nextImage : null;
  const focusKind = next?.meal_type ?? currentMealKind(now,dashboard.timezone);
  const nutritionRows = familyNutritionSummary(dashboard.members);
  const nutritionWithData = nutritionRows.filter(row => row.hasConfirmedConsumption || (row.planned !== null && row.planned > 0));
  const nutritionOverviewRows = nutritionWithData.slice(0, 4);
  const intakeRecordedPercent = dashboard.members.length ? Math.round(nutritionRows.filter(row=>row.hasConfirmedConsumption).length*100/dashboard.members.length) : 0;
  const energyNumber = new Intl.NumberFormat(locale,{maximumFractionDigits:0});
  const plannedMeals = dashboard.meals.filter(meal=>meal.status!=="cancelled").length;
  const kinds = ["breakfast", "lunch", "snack", "dinner"];
  const labels: Record<string,string> = pt ? {breakfast:"Pequeno-almoço",lunch:"Almoço",snack:"Lanche",dinner:"Jantar"} : {breakfast:"Breakfast",lunch:"Lunch",snack:"Snack",dinner:"Dinner"};
  const statusLabels: Record<string,string> = pt ? {planned:"Planeada",prepared:"Preparada",served:"Servida",completed:"Concluída"} : {planned:"Planned",prepared:"Prepared",served:"Served",completed:"Completed"};
  const openToday = () => onOpenWeek ? onOpenWeek(dashboard.dashboard_date) : onPlanMeal();
  const day = new Intl.DateTimeFormat(locale, {weekday:"long",day:"numeric",month:"long",timeZone:"UTC"}).format(new Date(dashboard.dashboard_date+"T12:00:00Z"));
  return <div className="family-home nf-home nf-home-reference-v4">
    <header className="screen-header nf-home-heading">
      <div><span className="eyebrow">{pt ? "O NOSSO DIA À MESA" : "OUR DAY AT THE TABLE"}</span><h1>{pt ? "Mais tempo juntos." : "More time together."}</h1><p>{pt ? "Uma refeição em comum. O cuidado certo para cada pessoa." : "One shared meal. The right care for each person."}</p></div>
      <button className="button primary" onClick={onPlanMeal} type="button"><Icon name="calendar"/>{pt ? "Planear a semana" : "Plan our week"}</button>
    </header>
    <div className="nf-home-grid">
      <section className="nf-meal-hero" aria-label={pt ? "Próxima refeição" : "Next meal"}>
        <div className="nf-meal-hero-copy"><span className="eyebrow">{pt ? "PRÓXIMA REFEIÇÃO" : "NEXT MEAL"}</span><small className="nf-home-hero-date">{day}</small>
          <h2>{next?.title ?? (next ? labels[next.meal_type] ?? next.meal_type : pt ? `O próximo ${(labels[focusKind] ?? "jantar").toLocaleLowerCase(locale)} começa aqui.` : `Your next ${(labels[focusKind] ?? "dinner").toLowerCase()} starts here.`)}</h2>
          <p>{pt ? "Escolhas partilhadas, com espaço para as necessidades de todos." : "Shared choices, with room for everyone’s needs."}</p>
          <button className="button primary" onClick={openToday} type="button">{next ? (pt ? "Ver refeições e porções" : "View meals & portions") : (pt ? "Escolher uma refeição" : "Choose a meal")}<Icon name="arrow"/></button>
          <div className="nf-hero-meta">{next && <span><Icon name="clock"/>{formatMealTime(next.scheduled_at,dashboard.timezone,locale)}</span>}<span><Icon name="people"/>{next?.participant_person_ids.length ?? dashboard.members.length} {pt ? "pessoas" : "people"}</span></div>
        </div>
        {shownHomeImage ? <img key={shownHomeImage.src} className="nf-meal-hero-art nf-meal-hero-photo"
          src={shownHomeImage.src} alt={shownHomeImage.alt} loading="eager" referrerPolicy="no-referrer"
          onError={() => setFailedHomeImage(shownHomeImage.src)} /> :
          <img className="nf-meal-hero-art" src="/images/shared-meal.svg" alt="" aria-hidden="true"/>}
        {shownHomeImage?.source && <a className="nf-home-photo-credit" href={shownHomeImage.source}
          target="_blank" rel="noopener noreferrer">
          {shownHomeImage.author} · {shownHomeImage.license}
        </a>}
      </section>
      <Panel className="nf-family-panel nf-family-nutrition-card" label={pt ? "Progresso nutricional da família" : "Family nutrition progress"}>
        <div className="nf-home-progress-head">
          <div><h2><Icon name="leaf"/>{pt ? "Progresso nutricional da família" : "Family nutrition progress"}</h2>
            <p>{pt ? "Registos do dia · energia planeada, não metas clínicas" : "Today's records · planned energy, not clinical targets"}</p></div>
        </div>
        <div className="nf-home-progress-body">
          <div className="nf-home-progress-gauge">
            <div className="nf-home-progress-ring" role="img"
              aria-label={pt ? `${intakeRecordedPercent}% dos membros com consumo registado hoje` : `${intakeRecordedPercent}% of members with recorded intake today`}
              style={{background:`conic-gradient(var(--color-action,#d8b28c) ${intakeRecordedPercent}%, var(--color-surface-soft,#302d2e) 0)`}}>
              <span><strong>{intakeRecordedPercent}%</strong><small>{pt ? "com registo" : "recorded"}</small></span>
            </div>
            <small>{pt ? "Consumo registado" : "Recorded intake"}</small>
          </div>
          <div className="nf-home-progress-measures">
            {nutritionOverviewRows.map(({member,consumed,planned,hasConfirmedConsumption,ratio})=>
              <div className="nf-home-progress-measure" key={member.person_id}>
                <div className="nf-home-progress-measure-title"><strong>{memberDisplayName(member)}</strong>
                  <span>{hasConfirmedConsumption ? `${energyNumber.format(consumed!)} kcal` : (pt ? "Sem registo" : "Not recorded")}</span></div>
                <div className="nf-home-progress-track" role={ratio!==null ? "progressbar" : undefined}
                  aria-valuenow={ratio??undefined} aria-valuemin={ratio!==null?0:undefined} aria-valuemax={ratio!==null?100:undefined}
                  aria-label={pt?`Consumo de ${memberDisplayName(member)} face à energia planeada`:`${memberDisplayName(member)} intake versus planned energy`}>
                  <span style={{width:`${ratio??0}%`}} />
                </div>
                <small>{planned!==null&&planned>0
                  ? (pt?`Planeado: ${energyNumber.format(planned)} kcal`:`Planned: ${energyNumber.format(planned)} kcal`)
                  : (pt?"Sem energia planeada":"No planned energy")}</small>
              </div>)}
            {!nutritionOverviewRows.length && <p className="nf-home-progress-empty">{pt?"Ainda não existem dados nutricionais registados hoje.":"No nutrition records available today."}</p>}
          </div>
        </div>
        <div className="nf-home-family-strip">
          <span>{pt ? "À mesa" : "At the table"}</span>
          <div className="nf-home-family-strip-members">
            {dashboard.members.map(member=><button type="button" className="nf-home-family-chip" key={member.person_id}
              onClick={()=>onOpenPerson(member.person_id)} title={memberDisplayName(member)}>
              <PersonAvatar identity={member.person_id} name={memberDisplayName(member)} familyIdentity={dashboard.family_id}
                age={member.age_years} sex={member.sex_for_energy_calculation} appearance={member.avatar_appearance} decorative/>
              <span>{member.first_name}</span>
            </button>)}
          </div>
          <span className="nf-home-family-strip-count">{dashboard.members.length} {pt?"perfis":"profiles"} · {plannedMeals} {pt?"refeições":"meals"}</span>
        </div>
      </Panel>
    </div>
    <section className="nf-today-section" aria-labelledby="today-heading">
      <div className="nf-panel-heading nf-today-editorial-heading">
        <div><h2 id="today-heading"><Icon name="calendar"/>{pt ? "O dia de hoje" : "Today"}</h2>
          <p>{pt ? `Plano da família para ${day}.` : `Family plan for ${day}.`}</p></div>
        <button className="button ghost small" onClick={openToday} type="button">{pt ? "Ver plano" : "View plan"}<Icon name="arrow"/></button>
      </div>
      <div className="nf-day-slots">{kinds.map(kind=>{
        const meals=dashboard.meals.filter(meal=>meal.meal_type===kind&&meal.status!=="cancelled");
        const meal=meals[0];
        return <button className={`nf-day-slot ${meal ? "" : "nf-day-slot-empty"}`} key={kind} type="button" onClick={openToday}>
          {meal ? <TodayMealPhoto title={meal.title}/> : <span className="nf-today-photo-fallback nf-today-photo-empty"><Icon name="coffee"/></span>}
          <span className="nf-day-slot-content">
            <span className="nf-day-slot-kind"><Icon name={kind==="breakfast"?"coffee":kind==="lunch"?"utensils":kind==="snack"?"apple":"cloche"}/>{labels[kind]}</span>
            <strong>{meal?.title ?? (pt ? "Por planear" : "To plan")}</strong>
            <span className="nf-slot-status">{meal ? statusLabels[meal.status]??meal.status : pt ? "Escolher refeição" : "Choose a meal"}</span>
          </span>
          {meal && <small>{formatMealTime(meal.scheduled_at,dashboard.timezone,locale)} · {meal.participant_person_ids.length} {pt ? "pessoas" : "people"}{meals.length>1?` · +${meals.length-1} ${pt?"refeições":"meals"}`:""}</small>}
        </button>;
      })}</div>
    </section>
    <section className="nf-home-actions-v3" aria-label={pt ? "Ações rápidas" : "Quick actions"}>
      <div className="nf-panel-heading"><h2>{pt ? "Ações rápidas" : "Quick actions"}</h2></div>
      <div className="nf-home-actions-v3-grid">
        <button type="button" onClick={onPlanMeal}><Icon name="calendar"/><strong>{pt?"Planear semana":"Plan week"}</strong></button>
        {onOpenRecipes && <button type="button" onClick={onOpenRecipes}><Icon name="book"/><strong>{pt?"Ver receitas":"View recipes"}</strong></button>}
        {onOpenShopping && <button type="button" onClick={onOpenShopping}><Icon name="bag"/><strong>{pt?"Criar lista de compras":"Shopping list"}</strong></button>}
        <button type="button" onClick={onAdaptPlan ?? onPlanMeal}><Icon name="spark"/><strong>{pt?"Adaptar plano":"Adapt plan"}</strong></button>
      </div>
    </section>
    {onOpenWeek && <section className="nf-home-weeks-v3" aria-label={pt ? "Planos da semana" : "Weekly plans"}>
      <div className="nf-panel-heading nf-home-weeks-v3-heading"><div><h2><Icon name="calendar"/>{pt ? "Planos da semana" : "Weekly plans"}</h2><small>{pt ? "Consultar a agenda da família" : "Browse the family calendar"}</small></div><button className="button ghost small" onClick={()=>onOpenWeek(calendarMonday(dashboard.dashboard_date))} type="button">{pt ? "Ver todos" : "View all"}<Icon name="arrow"/></button></div>
      <div className="nf-home-weeks-v3-grid">{([-7,0,7] as const).map(offset=>{
        const monday=calendarDateOffset(calendarMonday(weekDate??dashboard.dashboard_date),offset);
        const end=calendarDateOffset(monday,6);
        const dateLabel=(date:string)=>new Intl.DateTimeFormat(locale,{day:"numeric",month:"short",timeZone:"UTC"}).format(new Date(date+"T12:00:00Z"));
        return <button type="button" className={`nf-home-weeks-v3-card ${offset===0?"is-current":""}`} key={monday} onClick={()=>onOpenWeek(monday)}>
          <Icon name="calendar"/><strong>{offset===0?(pt?"Semana atual":"Current week"):offset<0?(pt?"Semana anterior":"Previous week"):(pt?"Próxima semana":"Next week")}</strong>
          <span>{dateLabel(monday)} – {dateLabel(end)}</span>{offset===0&&<small>{pt?"Esta semana":"This week"}</small>}
        </button>;
      })}</div>
      <details className="nf-home-week-details"><summary>{pt ? "Explorar refeições e alternativas guardadas" : "Explore saved meals and alternatives"}</summary><ScheduledWeeks initialWeek={weekDate} familyId={dashboard.family_id} referenceDate={dashboard.dashboard_date} onOpenWeek={onOpenWeek}/></details>
    </section>}
    <p className="nf-home-note">{t("home.familyHelp")}</p>
  </div>;
}
