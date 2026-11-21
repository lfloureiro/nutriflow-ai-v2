import {useEffect, useState} from "react";
import ScheduledWeeks from "./ScheduledWeeks";
import type {FamilyDashboard, FamilyDashboardMeal, FamilyDashboardMember} from "./api/types";
import {useI18n, type Locale} from "./i18n";
import Icon from "./ui/Icon";
import {resolveMealHeroImage} from "./mealHeroImages";
import PersonAvatar from "./ui/PersonAvatar";
import {EmptyState, Panel} from "./ui/primitives";
import "./planning-journey.css";

export function memberDisplayName(member: FamilyDashboardMember): string {
  return [member.first_name, member.last_name].filter(Boolean).join(" ");
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
    <span className="nf-today-photo-fallback" aria-hidden="true"><Icon name="book"/></span>;
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
  const kinds = ["breakfast", "lunch", "snack", "dinner"];
  const labels: Record<string,string> = pt ? {breakfast:"Pequeno-almoço",lunch:"Almoço",snack:"Lanche",dinner:"Jantar"} : {breakfast:"Breakfast",lunch:"Lunch",snack:"Snack",dinner:"Dinner"};
  const statusLabels: Record<string,string> = pt ? {planned:"Planeada",prepared:"Preparada",served:"Servida",completed:"Concluída"} : {planned:"Planned",prepared:"Prepared",served:"Served",completed:"Completed"};
  const openToday = () => onOpenWeek ? onOpenWeek(dashboard.dashboard_date) : onPlanMeal();
  const day = new Intl.DateTimeFormat(locale, {weekday:"long",day:"numeric",month:"long",timeZone:"UTC"}).format(new Date(dashboard.dashboard_date+"T12:00:00Z"));
  return <div className="family-home nf-home">
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
      <Panel className="nf-family-panel" label={pt ? "Pessoas da família" : "Family members"}>
        <div className="nf-family-progress-heading"><Icon name="leaf"/><strong>{pt?"Acompanhamento nutricional":"Nutrition overview"}</strong></div>
        <p className="nf-family-progress-sub">{pt?"Dados disponíveis dos perfis da família":"Available data from family profiles"}</p>
        <div className="nf-family-nutrition-lines">
          {dashboard.members.filter(person=>person.nutrition).map(person=><div key={person.person_id}>
            <span>{memberDisplayName(person)}</span>
            <strong>{person.nutrition?.energy_consumed_kcal ?? "—"} kcal</strong>
          </div>)}
          {!dashboard.members.some(person=>person.nutrition) && <small>{pt?"Ainda não existem dados nutricionais confirmados para hoje.":"No confirmed nutrition data for today."}</small>}
        </div>
        <div className="nf-panel-heading"><h2>{pt ? "Quem se senta à mesa" : "Who is at the table"}</h2><span className="nf-count">{dashboard.members.length}</span></div>
        {dashboard.members.map(member=><button className="nf-person-line" type="button" key={member.person_id} onClick={()=>onOpenPerson(member.person_id)}>
          <PersonAvatar identity={member.person_id} name={memberDisplayName(member)} familyIdentity={dashboard.family_id} age={member.age_years} sex={member.sex_for_energy_calculation} appearance={member.avatar_appearance} decorative/>
          <span className="nf-person-copy"><strong>{memberDisplayName(member)}</strong><small>{pt ? "Perfil, necessidades e rotina" : "Profile, needs and routine"}</small></span><Icon name="arrow"/>
        </button>)}
        {!dashboard.members.length && <EmptyState title={pt ? "Quem vem à mesa?" : "Who is joining?"} description={pt ? "Adiciona as pessoas em Família para começar." : "Add people in Family to get started."}/>}
        <p className="nf-panel-footnote">{pt ? "As necessidades de cada pessoa acompanham o planeamento." : "Each person’s needs accompany the plan."}</p>
      </Panel>
    </div>
    <section className="nf-today-section" aria-labelledby="today-heading">
      <div className="nf-panel-heading"><div><span className="eyebrow">{pt ? "QUATRO MOMENTOS, UM PLANO" : "FOUR MOMENTS, ONE PLAN"}</span><h2 id="today-heading">{pt ? "O dia, sem complicar" : "Your day, made simple"}</h2></div><button className="button ghost small" onClick={openToday} type="button">{pt ? "Abrir plano" : "Open plan"}<Icon name="arrow"/></button></div>
      <div className="nf-day-slots">{kinds.map(kind=>{
        const meals=dashboard.meals.filter(meal=>meal.meal_type===kind&&meal.status!=="cancelled");
        const meal=meals[0];
        return <button className={`nf-day-slot ${meal ? "" : "nf-day-slot-empty"}`} key={kind} type="button" onClick={openToday}>
          {meal && <TodayMealPhoto title={meal.title}/>}
          <span className="eyebrow">{labels[kind]}</span><span className="nf-slot-icon"><Icon name={kind === "breakfast" || kind === "snack" ? "leaf" : "book"}/></span>
          <strong>{meal?.title ?? (meal ? labels[kind] : pt ? "Por planear" : "To plan")}</strong>
          <span className="nf-slot-status">{meal ? statusLabels[meal.status]??meal.status : pt ? "Escolher refeição" : "Choose a meal"}</span>
          {meal && <small>{formatMealTime(meal.scheduled_at,dashboard.timezone,locale)} · {meal.participant_person_ids.length} {pt ? "pessoas" : "people"}{meals.length>1?` · +${meals.length-1} ${pt?"refeições":"meals"}`:""}</small>}
        </button>;
      })}</div>
    </section>
    <section className="nf-home-shortcuts" aria-label={pt ? "Ações rápidas" : "Quick actions"}>
      <div className="nf-panel-heading"><h2>{pt ? "Ações rápidas" : "Quick actions"}</h2></div>
      <div className="nf-home-shortcut-grid">
        <button type="button" onClick={onPlanMeal}><Icon name="calendar"/><strong>{pt?"Planear semana":"Plan week"}</strong></button>
        {onOpenRecipes && <button type="button" onClick={onOpenRecipes}><Icon name="book"/><strong>{pt?"Ver receitas":"View recipes"}</strong></button>}
        {onOpenShopping && <button type="button" onClick={onOpenShopping}><Icon name="bag"/><strong>{pt?"Criar lista de compras":"Shopping list"}</strong></button>}
        <button type="button" onClick={onAdaptPlan ?? onPlanMeal}><Icon name="spark"/><strong>{pt?"Adaptar plano":"Adapt plan"}</strong></button>
      </div>
    </section>
    {onOpenWeek && <details className="nf-saved-weeks"><summary><span><Icon name="calendar"/>{pt ? "Consultar as nossas semanas guardadas" : "Browse our saved weeks"}</span><span>{pt ? "Ver semanas" : "View weeks"}</span></summary><ScheduledWeeks initialWeek={weekDate} familyId={dashboard.family_id} referenceDate={dashboard.dashboard_date} onOpenWeek={onOpenWeek}/></details>}
    <p className="nf-home-note">{t("home.familyHelp")}</p>
  </div>;
}
