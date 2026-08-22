import { useEffect, useMemo, useState, type FormEvent } from "react";

import { ApiError, getFamilyDashboard } from "./api/client";
import type { FamilyDashboard } from "./api/types";
import FamilyHome, { memberDisplayName } from "./FamilyHome";
import FamilyMealsScreen, { type FamilyMealsMode } from "./FamilyMeals";
import { useI18n, type Locale } from "./i18n";
import PersonOverview from "./PersonOverview";
import { useTheme, type Appearance } from "./theme";

const DEMO_FAMILY_ID = "11111111-1111-4111-8111-111111111111";
const FAMILY_STORAGE_KEY = "nutriflow-family-id";

type View = "home" | "meals" | "people" | "house" | "more";

type NavItem = {
  view: View;
  icon: string;
  labelKey: "nav.home" | "nav.meals" | "nav.people" | "nav.house" | "nav.more";
};

const NAV_ITEMS: NavItem[] = [
  { view: "home", icon: "⌂", labelKey: "nav.home" },
  { view: "meals", icon: "◫", labelKey: "nav.meals" },
  { view: "people", icon: "◎", labelKey: "nav.people" },
  { view: "house", icon: "▣", labelKey: "nav.house" },
  { view: "more", icon: "•••", labelKey: "nav.more" },
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

function PlaceholderScreen({
  eyebrow,
  title,
  text,
}: {
  eyebrow: string;
  title: string;
  text: string;
}) {
  return (
    <div className="placeholder-screen">
      <span className="eyebrow">{eyebrow}</span>
      <h1>{title}</h1>
      <p>{text}</p>
    </div>
  );
}

export default function App() {
  const { locale, setLocale, t } = useI18n();
  const { appearance, setAppearance } = useTheme();
  const initialId = useMemo(initialFamilyId, []);

  const [familyInput, setFamilyInput] = useState(initialId);
  const [activeFamilyId, setActiveFamilyId] = useState(initialId);
  const [dashboard, setDashboard] = useState<FamilyDashboard | null>(null);
  const [dashboardBusy, setDashboardBusy] = useState(initialId.length > 0);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [dashboardRevision, setDashboardRevision] = useState(0);
  const [view, setView] = useState<View>("home");
  const [selectedPersonId, setSelectedPersonId] = useState<string | null>(null);
  const [mealsMode, setMealsMode] = useState<FamilyMealsMode>("today");

  useEffect(() => {
    if (!activeFamilyId || view !== "home") {
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
  }, [activeFamilyId, dashboardRevision, view]);

  function handleConnect(event: FormEvent) {
    event.preventDefault();
    const nextFamilyId = familyInput.trim();
    if (!nextFamilyId) {
      setDashboardError(t("validation.familyRequired"));
      return;
    }
    setDashboard(null);
    setDashboardError(null);
    setSelectedPersonId(null);
    setMealsMode("today");
    setView("home");
    setActiveFamilyId(nextFamilyId);
    setDashboardRevision((current) => current + 1);
  }

  function openPerson(personId: string) {
    setSelectedPersonId(personId);
    setView("people");
  }

  function openPrimaryView(nextView: View) {
    if (nextView === "people") {
      setSelectedPersonId(null);
    }
    if (nextView === "meals") {
      setMealsMode("today");
    }
    setView(nextView);
  }

  function openMealRecommendation() {
    setMealsMode("recommend");
    setView("meals");
  }

  function changeFamily() {
    window.localStorage.removeItem(FAMILY_STORAGE_KEY);
    setDashboard(null);
    setDashboardError(null);
    setActiveFamilyId("");
    setFamilyInput("");
    setSelectedPersonId(null);
    setMealsMode("today");
    setView("home");
  }

  if (!activeFamilyId || (view === "home" && !dashboard && !dashboardBusy)) {
    return (
      <main className="entry-screen">
        <div className="entry-card">
          <div className="entry-brand">
            <span className="brand-mark" aria-hidden="true">
              N
            </span>
            <strong>{t("app.brand")}</strong>
          </div>
          <div>
            <span className="eyebrow">{t("entry.eyebrow")}</span>
            <h1>{t("entry.title")}</h1>
            <p>{t("entry.help")}</p>
          </div>
          {dashboardError ? (
            <div className="error-banner" role="alert">
              <strong>{t("error.title")}</strong>
              <span>{dashboardError}</span>
            </div>
          ) : null}
          <form className="stack" onSubmit={handleConnect}>
            <label className="field">
              <span>{t("setup.familyId")}</span>
              <input
                autoComplete="off"
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                value={familyInput}
                onChange={(event) => setFamilyInput(event.target.value)}
              />
            </label>
            <button className="button primary large" type="submit">
              {t("entry.open")}
            </button>
          </form>
          <div className="entry-preferences">
            <label className="compact-control">
              <span>{t("nav.language")}</span>
              <select value={locale} onChange={(event) => setLocale(event.target.value as Locale)}>
                <option value="pt-PT">PT</option>
                <option value="en">EN</option>
              </select>
            </label>
            <label className="compact-control">
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
          </div>
        </div>
      </main>
    );
  }

  const familyName = dashboard?.family_name ?? t("app.brand");
  const selectedMember = dashboard?.members.find(
    (member) => member.person_id === selectedPersonId,
  );

  return (
    <div className="app-shell">
      <aside className="side-nav">
        <button className="side-brand" onClick={() => openPrimaryView("home")} type="button">
          <span className="brand-mark" aria-hidden="true">
            N
          </span>
          <span>{t("app.brand")}</span>
        </button>
        <nav className="primary-nav" aria-label={t("nav.primary")}>
          {NAV_ITEMS.map((item) => (
            <button
              aria-current={view === item.view ? "page" : undefined}
              className={`nav-item ${view === item.view ? "active" : ""}`}
              key={item.view}
              onClick={() => openPrimaryView(item.view)}
              type="button"
            >
              <span className="nav-icon" aria-hidden="true">
                {item.icon}
              </span>
              <span>{t(item.labelKey)}</span>
            </button>
          ))}
        </nav>
        <div className="side-nav__family">
          <span>{t("shell.family")}</span>
          <strong>{familyName}</strong>
        </div>
      </aside>

      <div className="shell-content">
        <header className="shell-topbar">
          <div>
            <span className="shell-topbar__label">{t("shell.family")}</span>
            <strong>{familyName}</strong>
          </div>
          <button
            aria-label={t("home.refresh")}
            className="shell-icon-button"
            disabled={dashboardBusy}
            onClick={() => {
              setView("home");
              setDashboardRevision((current) => current + 1);
            }}
            type="button"
          >
            ↻
          </button>
        </header>

        <main className="shell-main">
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
                dashboard={dashboard}
                onOpenPerson={openPerson}
                onPlanMeal={openMealRecommendation}
              />
            )
          ) : null}

          {view === "meals" ? (
            <FamilyMealsScreen
              familyId={activeFamilyId}
              mode={mealsMode}
              onModeChange={setMealsMode}
              referenceDate={dashboard?.dashboard_date}
            />
          ) : null}

          {view === "people" ? (
            selectedMember && dashboard ? (
              <PersonOverview
                dashboard={dashboard}
                member={selectedMember}
                onBack={() => setSelectedPersonId(null)}
              />
            ) : (
              <div className="people-screen">
                <header className="screen-header compact-screen-header">
                  <div>
                    <span className="eyebrow">{t("nav.people")}</span>
                    <h1>{t("people.title")}</h1>
                    <p>{t("people.help")}</p>
                  </div>
                </header>
                <div className="people-list">
                  {dashboard?.members.map((member) => (
                    <button
                      className="person-row"
                      key={member.person_id}
                      onClick={() => setSelectedPersonId(member.person_id)}
                      type="button"
                    >
                      <span className="member-avatar" aria-hidden="true">
                        {member.first_name.slice(0, 1).toUpperCase()}
                      </span>
                      <span>
                        <strong>{memberDisplayName(member)}</strong>
                        <small>{member.timezone}</small>
                      </span>
                      <span aria-hidden="true">›</span>
                    </button>
                  ))}
                </div>
              </div>
            )
          ) : null}

          {view === "house" ? (
            <PlaceholderScreen
              eyebrow={t("nav.house")}
              text={t("house.help")}
              title={t("house.title")}
            />
          ) : null}

          {view === "more" ? (
            <div className="settings-screen">
              <header className="screen-header compact-screen-header">
                <div>
                  <span className="eyebrow">{t("nav.more")}</span>
                  <h1>{t("more.title")}</h1>
                  <p>{t("more.help")}</p>
                </div>
              </header>
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
                    {t("more.changeFamily")}
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
            <span aria-hidden="true">{item.icon}</span>
            <small>{t(item.labelKey)}</small>
          </button>
        ))}
      </nav>
    </div>
  );
}
