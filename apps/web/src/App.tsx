import {requestNavigation,useAppRoute,type AppView,type HouseView} from "./navigation";
import { lazy, Suspense, useEffect, useMemo, useState } from "react";

import { ApiError, getFamilyDashboard } from "./api/client";
import type { Family } from "./api/setupTypes";
import type { FamilyDashboard } from "./api/types";
import FamilyEntryScreen from "./FamilyEntryScreen";
import FamilyHome, { memberDisplayName } from "./FamilyHome";
import type { FamilyMealsMode } from "./FamilyMeals";
const FamilyMealsScreen = lazy(() => import("./FamilyMeals"));
const FamilySettings = lazy(() => import("./FamilySettings"));
import Brand from "./ui/Brand";
import ContextDrawer from "./ui/ContextDrawer";
import Icon, {type IconName} from "./ui/Icon";
import PersonAvatar from "./ui/PersonAvatar";
const HomeBase = lazy(() => import("./HomeBase"));
import { useI18n, type Locale } from "./i18n";
const PersonOverview = lazy(() => import("./PersonOverview"));
const PersonSetupForm = lazy(() => import("./PersonSetupForm"));
const ShoppingListScreen = lazy(() => import("./ShoppingListScreen"));
import { useTheme, type Appearance } from "./theme";

const DEMO_FAMILY_ID = "11111111-1111-4111-8111-111111111111";
const FAMILY_STORAGE_KEY = "nutriflow-family-id";

type View = AppView;

type NavItem = {
  view: View;
  icon: IconName;
  labelKey: "nav.home" | "nav.meals" | "nav.people" | "nav.house" | "nav.shopping";
};

const NAV_ITEMS: NavItem[] = [
  { view: "home", icon: "home", labelKey: "nav.home" },
  { view: "meals", icon: "calendar", labelKey: "nav.meals" },
  { view: "house", icon: "book", labelKey: "nav.house" },
  { view: "people", icon: "people", labelKey: "nav.people" },
  { view: "shopping", icon: "bag", labelKey: "nav.shopping" },
];

function initialFamilyId(): string {
  const stored = window.localStorage.getItem(FAMILY_STORAGE_KEY);
  if (stored && stored.trim()) {
    return stored.trim();
  }
  return import.meta.env.DEV ? DEMO_FAMILY_ID : "";
}

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.message} (HTTP ${error.status})`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

export default function App() {
  const { locale, setLocale, t } = useI18n();
  const { appearance, setAppearance } = useTheme();
  const initialId = useMemo(initialFamilyId, []);

  const [activeFamilyId, setActiveFamilyId] = useState(initialId);
  const [dashboard, setDashboard] = useState<FamilyDashboard | null>(null);
  const [dashboardBusy, setDashboardBusy] = useState(initialId.length > 0);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [dashboardRevision, setDashboardRevision] = useState(0);
  const {route,navigate}=useAppRoute();
  const view=route.view;const setView=(view:View)=>navigate({view});
  const houseInitialView=route.house;const setHouseInitialView=(house:HouseView)=>navigate({house});
  useEffect(()=>{window.scrollTo(0,0);},[view]);
  const selectedPersonId=route.person??null;const setSelectedPersonId=(person:string|null)=>navigate({person:person??undefined});
  const [showPersonSetup, setShowPersonSetup] = useState(false);
  const mealsDate=route.date;const setMealsDate=(date:string|undefined)=>navigate({date,meal:undefined});
  const mealsMode=route.mode;const setMealsMode=(mode:FamilyMealsMode)=>navigate({mode,meal:undefined});

  useEffect(() => {
    if (!activeFamilyId) {
      return;
    }

    let cancelled = false;
    setDashboardBusy(true);
    setDashboardError(null);
    void getFamilyDashboard(activeFamilyId)
      .then((result) => {
        if (cancelled) {
          return;
        }
        setDashboard(result);
        window.localStorage.setItem(FAMILY_STORAGE_KEY, activeFamilyId);
      })
      .catch((caught: unknown) => {
        if (cancelled) {
          return;
        }
        setDashboard(null);
        setDashboardError(errorText(caught));
      })
      .finally(() => {
        if (!cancelled) {
          setDashboardBusy(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [activeFamilyId, dashboardRevision]);

  function refreshDashboard() {
    setDashboardRevision((current) => current + 1);
  }

  function openFamily(nextFamilyId: string) {
    const normalized = nextFamilyId.trim();
    if (!normalized) {
      setDashboardError(t("validation.familyRequired"));
      return;
    }
    if(!navigate({view:"home",mode:"today",date:undefined,person:undefined,house:"recipes"}))return false;
    setDashboard(null);setDashboardError(null);setShowPersonSetup(false);setActiveFamilyId(normalized);refreshDashboard();return true;
  }
  function handleFamilyCreated(family: Family) {
    if(!openFamily(family.id))return;
    navigate({view:"people"});setShowPersonSetup(true);
  }

  function openPerson(personId: string) {
    setShowPersonSetup(false);
    navigate({person:personId,view:"people"});
  }

  function openPrimaryView(nextView: View) {
    if(!navigate({view:nextView,...(nextView==="people"?{person:undefined}:{}),...(nextView==="meals"?{mode:"week" as const,meal:undefined}:{}),...(nextView==="house"?{house:"recipes" as const}:{})}))return;
    if(nextView==="people")setShowPersonSetup(false);
  }
  function openWeek(date:string){navigate({date,mode:"week",view:"meals",meal:undefined});}
  function openMealPlan(){navigate({date:undefined,mode:"prepare",view:"meals",meal:undefined});}

  function changeFamily() {
    if(!navigate({view:"home",mode:"today",date:undefined,person:undefined,house:"recipes"}))return;
    window.localStorage.removeItem(FAMILY_STORAGE_KEY);setDashboard(null);setDashboardError(null);setActiveFamilyId("");setShowPersonSetup(false);
  }

  if (!activeFamilyId || (view === "home" && !dashboard && !dashboardBusy)) {
    return (
      <FamilyEntryScreen
        externalError={dashboardError}
        initialFamilyId={initialId}
        onCreated={handleFamilyCreated}
        onOpenExisting={openFamily}
      />
    );
  }

  const familyName = dashboard?.family_name ?? t("app.brand");
  const selectedMember = dashboard?.members.find(
    (member) => member.person_id === selectedPersonId,
  );

  return (
    <div className={`app-shell${view === "meals" ? " app-shell--meals" : ""}`}>
      <aside className="side-nav">
        <button className="side-brand" onClick={() => openPrimaryView("home")} type="button">
          <Brand />
        </button>
        <nav className="primary-nav" aria-label={t("nav.primary")}>
          {NAV_ITEMS.map((item) => (
            <button
              aria-current={view === item.view && (item.view !== "house" || houseInitialView !== "pantry") ? "page" : undefined}
              className={`nav-item ${view === item.view && (item.view !== "house" || houseInitialView !== "pantry") ? "active" : ""}`}
              key={item.view}
              onClick={() => openPrimaryView(item.view)}
              type="button"
            >
              <span className="nav-icon" aria-hidden="true">
                <Icon name={item.icon}/>
              </span>
              <span>{item.view === "meals" ? (locale === "pt-PT" ? "A nossa semana" : "Our week") : item.view === "house" ? (locale === "pt-PT" ? "Receitas" : "Recipes") : item.view === "people" ? (locale === "pt-PT" ? "Família" : "Family") : t(item.labelKey)}</span>
            </button>
          ))}
          <button
            aria-current={view === "house" && houseInitialView === "pantry" ? "page" : undefined}
            className={`nav-item ${view === "house" && houseInitialView === "pantry" ? "active" : ""}`}
            onClick={() => navigate({view:"house",house:"pantry"})}
            type="button"
          >
            <span className="nav-icon" aria-hidden="true"><Icon name="pantry"/></span>
            <span>{locale === "pt-PT" ? "Despensa" : "Pantry"}</span>
          </button>
        </nav>
        <button className="side-nav__ai" type="button" onClick={() => navigate({view:"meals",mode:"recommend",meal:undefined})}>
          <span className="side-nav__ai-heading"><Icon name="spark"/><strong>{locale === "pt-PT" ? "Inteligência à mesa" : "Intelligence at the table"}</strong></span>
          <span>{locale === "pt-PT" ? "Interpretar. Aprender. Explicar." : "Interpret. Learn. Explain."}</span>
        </button>
        <button className="side-nav__family" type="button" onClick={() => setView("more")}
          aria-label={locale === "pt-PT" ? `Gerir o espaço: ${familyName}` : `Manage family space: ${familyName}`}>
          <span className="side-nav__family-avatar" aria-hidden="true">
            {familyName.trim().split(/\s+/).at(-1)?.charAt(0).toUpperCase() || "F"}
          </span>
          <span className="side-nav__family-copy">
            <strong>{familyName}</strong>
            <small>{locale === "pt-PT" ? "Gerir o nosso espaço" : "Manage our space"}</small>
          </span>
        </button>
      </aside>

      <div className="shell-content">
        <header className="shell-topbar">
          <div>
            <span className="shell-topbar__label">{t("shell.family")}</span>
            <strong>{familyName}</strong>
          </div>
          <div className="nf-topbar-actions">
            <select className="nf-appearance" aria-label={t("nav.appearance")} value={appearance} onChange={event=>setAppearance(event.target.value as Appearance)}>
              <option value="light">{t("theme.light")}</option><option value="dark">{t("theme.dark")}</option><option value="system">{t("theme.system")}</option>
            </select>
            <select className="nf-locale" aria-label={t("nav.language")} value={locale} onChange={event=>setLocale(event.target.value as Locale)}><option value="pt-PT">PT</option><option value="en">EN</option></select>
            <button className="shell-icon-button nf-settings-button" type="button" aria-label={locale === "pt-PT" ? "Definições e integrações" : "Settings and integrations"} title={locale === "pt-PT" ? "Definições da família e integrações" : "Family settings and integrations"} aria-current={view === "more" ? "page" : undefined} onClick={() => setView("more")}><Icon name="settings"/><span className="nf-settings-label">{locale === "pt-PT" ? "Definições" : "Settings"}</span></button>
          <button
            aria-label={t("home.refresh")}
            className="shell-icon-button"
            disabled={dashboardBusy}
            onClick={() => {
              refreshDashboard();
            }}
            type="button"
          >
            <Icon name="refresh"/>
          </button>
          </div>
        </header>

        <main className="shell-main">
          <header className="nf-print-header"><Brand/><span>{dashboard?.family_name}</span></header>
          {dashboardError ? (
            <div className="error-banner" role="alert">
              <strong>{t("error.title")}</strong>
              <span>{dashboardError}</span>
            </div>
          ) : null}

          {view === "home" ? (
            dashboardBusy || !dashboard ? (
              <div className="shell-loading" role="status">
                {t("home.loading")}
              </div>
            ) : (
              <FamilyHome
              onOpenRecipes={()=>openPrimaryView("house")} onOpenShopping={()=>openPrimaryView("shopping")}
                dashboard={dashboard}
                onOpenPerson={openPerson}
                onPlanMeal={openMealPlan}
                onAdaptPlan={()=>navigate({view:"meals",mode:"recommend",meal:undefined})}
                onOpenWeek={openWeek}
                weekDate={mealsDate}
              />
            )
          ) : null}

          {view === "meals" ? (
            <Suspense fallback={<div className="shell-loading" role="status">{t("home.loading")}</div>}><FamilyMealsScreen
              familyId={activeFamilyId}
              mode={mealsMode}
              onDataChanged={refreshDashboard}
              onModeChange={setMealsMode}
              initialDate={mealsDate}
              onDateChange={setMealsDate}
              selectedMealType={route.meal}
              onMealSelectionChange={(selection) => navigate({date:selection?.date ?? route.date,meal:selection?.mealType,view:"meals",mode:"week"})}
              referenceDate={dashboard?.dashboard_date}
            /></Suspense>
          ) : null}

          {view === "people" ? (
            <div className="people-screen">
              <header className="screen-header compact-screen-header people-screen-header">
                <div>
                  <span className="eyebrow">{t("nav.people")}</span>
                  <h1>{t("people.title")}</h1>
                  <p>{t("people.help")}</p>
                </div>
                <div className="nf-people-hero-avatars" aria-hidden="true">
                  {dashboard?.members.slice(0,4).map(member=><PersonAvatar key={member.person_id}
                    identity={member.person_id} name={memberDisplayName(member)}
                    familyIdentity={activeFamilyId} age={member.age_years}
                    sex={member.sex_for_energy_calculation} appearance={member.avatar_appearance} decorative/>)}
                </div>
                <button
                  className="button primary"
                  onClick={() => {if(requestNavigation())setShowPersonSetup((current) => !current);}}
                  type="button"
                >
                  {showPersonSetup
                    ? locale === "pt-PT"
                      ? "Fechar"
                      : "Close"
                    : locale === "pt-PT"
                      ? "+ Adicionar pessoa"
                      : "+ Add person"}
                </button>
              </header>
              <div className="nf-family-main-grid">
                <section className="nf-family-member-section">
                  <div className="nf-family-section-header">
                    <h2>{locale === "pt-PT" ? "Membros da família" : "Family members"}</h2>
                    <small>{dashboard?.members.length ?? 0} {locale === "pt-PT" ? "membros" : "members"}</small>
                  </div>
                  <div className="people-list">
                {dashboard?.members.map((member) => (
                  <button
                    className="person-row"
                    key={member.person_id}
                    onClick={() => openPerson(member.person_id)}
                    type="button"
                  >
                    <PersonAvatar identity={member.person_id} name={memberDisplayName(member)} familyIdentity={activeFamilyId} age={member.age_years} sex={member.sex_for_energy_calculation} appearance={member.avatar_appearance} decorative />
                    <span>
                      <strong>{memberDisplayName(member)}</strong>
                      <small>{dashboard?.meals.some(meal=>meal.status!=="cancelled"&&meal.participant_person_ids.includes(member.person_id))
                        ? (locale==="pt-PT"?"No plano de hoje":"In today's plan")
                        : (locale==="pt-PT"?"Sem refeição no plano de hoje":"No meal in today's plan")}</small>
                    </span>
                    <span aria-hidden="true">›</span>
                  </button>
                ))}
                  </div>
                </section>
                <aside className="nf-family-objectives">
                  <div className="nf-family-section-header">
                    <h2>{locale === "pt-PT" ? "Objetivos da família" : "Family goals"}</h2>
                  </div>
                  <div className="nf-family-goal-facts">
                    <div><strong>{dashboard?.members.length ?? 0}</strong><span>{locale==="pt-PT"?"perfis familiares":"family profiles"}</span></div>
                    <div><strong>{dashboard?.members.filter(member=>Number(member.nutrition?.energy_planned_kcal??0)>0).length ?? 0}</strong><span>{locale==="pt-PT"?"com energia planeada hoje":"with planned energy today"}</span></div>
                    <div><strong>{dashboard?.members.filter(member=>Number(member.nutrition?.energy_consumed_kcal??0)>0).length ?? 0}</strong><span>{locale==="pt-PT"?"com consumo registado":"with recorded intake"}</span></div>
                  </div>
                  <small className="nf-family-goal-disclaimer">{locale==="pt-PT"?"Valores do plano, não metas clínicas.":"Planning data, not clinical targets."}</small>
                  <button type="button" className="button ghost small" onClick={() => setView("more")}>
                    {locale === "pt-PT" ? "Gerir o espaço" : "Manage household"}
                  </button>
                </aside>
              </div>
              <div className="nf-family-insights">
                <section className="nf-family-preferences">
                  <div className="nf-family-section-header">
                    <h2>{locale === "pt-PT" ? "Resumo de preferências e restrições" : "Preferences and restrictions"}</h2>
                  </div>
                  <div className="nf-family-preference-placeholder">
                    <Icon name="leaf"/>
                    <p>{locale==="pt-PT"
                      ?"Preferências e restrições são consultadas em cada perfil. Não são presumidas a partir das refeições planeadas."
                      :"Preferences and restrictions are reviewed in each profile, never inferred from planned meals."}</p>
                  </div>
                </section>
                <section className="nf-family-comparison">
                  <div className="nf-family-section-header">
                    <h2>{locale === "pt-PT" ? "Perfis da família" : "Family profiles"}</h2>
                  </div>
                  <div className="nf-family-comparison-list">
                    {dashboard?.members.map((member) => <button key={member.person_id} type="button"
                      onClick={() => openPerson(member.person_id)}>
                      <strong>{memberDisplayName(member)}</strong>
                      <span>{locale === "pt-PT" ? "Ver preferências e necessidades" : "View preferences and needs"}</span>
                      <Icon name="arrow"/>
                    </button>)}
                  </div>
                </section>
              </div>
              {showPersonSetup && dashboard ? (
                <ContextDrawer
                  title={locale === "pt-PT" ? "Adicionar pessoa" : "Add person"}
                  wide
                  closeLabel={locale === "pt-PT" ? "Fechar detalhe" : "Close detail"}
                  onRequestClose={() => {if(!requestNavigation())return false;setShowPersonSetup(false);return true;}}
                >
                  <Suspense fallback={<p role="status">{t("home.loading")}</p>}><PersonSetupForm
                    familyId={activeFamilyId}
                    familyTimezone={dashboard.timezone}
                    onCancel={() => setShowPersonSetup(false)}
                    onCreated={() => { setShowPersonSetup(false); refreshDashboard(); }}
                  /></Suspense>
                </ContextDrawer>
              ) : null}
              {selectedMember && dashboard ? (
                <ContextDrawer
                  title={memberDisplayName(selectedMember)}
                  wide
                  closeLabel={locale === "pt-PT" ? "Fechar detalhe" : "Close detail"}
                  onRequestClose={() => setSelectedPersonId(null)}
                >
                  <Suspense fallback={<p role="status">{t("home.loading")}</p>}><PersonOverview
                    key={selectedMember.person_id}
                    dashboard={dashboard}
                    member={selectedMember}
                    onBack={() => setSelectedPersonId(null)}
                    onDataChanged={refreshDashboard}
                  /></Suspense>
                </ContextDrawer>
              ) : null}
            </div>
          ) : null}

          {view === "house" ? <Suspense fallback={<p role="status">{t("home.loading")}</p>}><HomeBase key={activeFamilyId} familyId={activeFamilyId} initialView={houseInitialView} onViewChange={setHouseInitialView} /></Suspense> : null}
          {view === "shopping" ? <Suspense fallback={<p role="status">{t("home.loading")}</p>}><ShoppingListScreen key={activeFamilyId} familyId={activeFamilyId} onOpenPantry={()=>navigate({view:"house",house:"pantry"})} /></Suspense> : null}

          {view === "more" ? (
            <div className="settings-screen">
              <header className="screen-header compact-screen-header">
                <div>
                  <span className="eyebrow">{t("nav.more")}</span>
                  <h1>{t("more.title")}</h1>
                  <p>{t("more.help")}</p>
                </div>
              </header>
              <Suspense fallback={<p role="status">{t("home.loading")}</p>}><FamilySettings
                familyId={activeFamilyId}
                onSaved={() => refreshDashboard()}
              /></Suspense>
              <section className="settings-card">
                <label className="field">
                  <span>{t("nav.language")}</span>
                  <select value={locale} onChange={(event) => setLocale(event.target.value as Locale)}>
                    <option value="pt-PT">Português</option>
                    <option value="en">English</option>
                  </select>
                </label>
                <label className="field">
                  <span>{t("nav.appearance")}</span>
                  <select
                    value={appearance}
                    onChange={(event) => setAppearance(event.target.value as Appearance)}
                  >
                    <option value="system">{t("theme.system")}</option>
                    <option value="light">{t("theme.light")}</option>
                    <option value="dark">{t("theme.dark")}</option>
                  </select>
                </label>
                <div className="settings-family-row">
                  <div>
                    <span>{t("shell.family")}</span>
                    <strong>{familyName}</strong>
                  </div>
                  <button className="button ghost" onClick={changeFamily} type="button">
                    {locale === "pt-PT" ? "Mudar / criar família" : "Change / create family"}
                  </button>
                </div>
              </section>
            </div>
          ) : null}
        </main>
      </div>

      <nav className="bottom-nav" aria-label={t("nav.primary")}>
        {NAV_ITEMS.map((item) => (
          <button
            aria-current={view === item.view ? "page" : undefined}
            className={view === item.view ? "active" : ""}
            key={item.view}
            onClick={() => openPrimaryView(item.view)}
            type="button"
          >
            <span aria-hidden="true"><Icon name={item.icon}/></span>
            <small>{item.view === "house" ? (locale === "pt-PT" ? "Receitas" : "Recipes") : item.view === "people" ? (locale === "pt-PT" ? "Família" : "Family") : t(item.labelKey)}</small>
          </button>
        ))}
      </nav>
    </div>
  );
}
