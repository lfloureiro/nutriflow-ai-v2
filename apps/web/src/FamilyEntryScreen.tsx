import { useMemo, useState, type FormEvent } from "react";

import { ApiError } from "./api/client";
import { createFamily } from "./api/setupClient";
import type { Family } from "./api/setupTypes";
import { useI18n, type Locale } from "./i18n";
import { useTheme, type Appearance } from "./theme";
import { supportedTimezones } from "./timezones";

const COPY = {
  "pt-PT": {
    create: "Criar família",
    open: "Abrir existente",
    createTitle: "Criar o espaço da família",
    createHelp:
      "Começa pela família. Depois adicionas as pessoas e o NutriFlow calcula os objetivos energéticos individuais.",
    familyName: "Nome da família",
    timezone: "Fuso horário",
    createButton: "Criar família",
    creating: "A criar…",
    openTitle: "Abrir uma família existente",
    openHelp:
      "Enquanto não existe autenticação, podes continuar a abrir uma família pelo respetivo ID.",
    familyId: "ID da família",
    openButton: "Abrir família",
    error: "Não foi possível criar a família",
  },
  en: {
    create: "Create family",
    open: "Open existing",
    createTitle: "Create the family space",
    createHelp:
      "Start with the family. Then add people and NutriFlow will calculate each person's energy targets.",
    familyName: "Family name",
    timezone: "Timezone",
    createButton: "Create family",
    creating: "Creating…",
    openTitle: "Open an existing family",
    openHelp:
      "Until authentication is available, an existing family can still be opened by ID.",
    familyId: "Family ID",
    openButton: "Open family",
    error: "Could not create the family",
  },
} as const;

function errorText(error: unknown): string {
  if (error instanceof ApiError) return `${error.message} (HTTP ${error.status})`;
  return error instanceof Error ? error.message : String(error);
}

export default function FamilyEntryScreen({
  initialFamilyId,
  externalError,
  onOpenExisting,
  onCreated,
}: {
  initialFamilyId: string;
  externalError: string | null;
  onOpenExisting: (familyId: string) => void;
  onCreated: (family: Family) => void;
}) {
  const { locale, setLocale } = useI18n();
  const { appearance, setAppearance } = useTheme();
  const copy = COPY[locale];
  const timezoneOptions = useMemo(supportedTimezones, []);
  const [mode, setMode] = useState<"create" | "open">("create");
  const [familyId, setFamilyId] = useState(initialFamilyId);
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState("Europe/Lisbon");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submitCreate(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const family = await createFamily({ name: name.trim(), timezone });
      onCreated(family);
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  function submitOpen(event: FormEvent) {
    event.preventDefault();
    onOpenExisting(familyId.trim());
  }

  return (
    <main className="entry-screen">
      <div className="entry-card family-entry-card">
        <div className="entry-brand">
          <span className="brand-mark" aria-hidden="true">
            N
          </span>
          <strong>NutriFlow AI</strong>
        </div>
        <div className="segmented-control family-entry-mode">
          <button
            className={mode === "create" ? "active" : ""}
            onClick={() => setMode("create")}
            type="button"
          >
            {copy.create}
          </button>
          <button
            className={mode === "open" ? "active" : ""}
            onClick={() => setMode("open")}
            type="button"
          >
            {copy.open}
          </button>
        </div>
        {error || externalError ? (
          <div className="error-banner" role="alert">
            <strong>{copy.error}</strong>
            <span>{error ?? externalError}</span>
          </div>
        ) : null}
        {mode === "create" ? (
          <form className="stack" onSubmit={submitCreate}>
            <div>
              <span className="eyebrow">{copy.create}</span>
              <h1>{copy.createTitle}</h1>
              <p>{copy.createHelp}</p>
            </div>
            <label className="field">
              <span>{copy.familyName}</span>
              <input
                required
                maxLength={120}
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            <label className="field">
              <span>{copy.timezone}</span>
              <select required value={timezone} onChange={(event) => setTimezone(event.target.value)}>
                {timezoneOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <button className="button primary large" disabled={busy} type="submit">
              {busy ? copy.creating : copy.createButton}
            </button>
          </form>
        ) : (
          <form className="stack" onSubmit={submitOpen}>
            <div>
              <span className="eyebrow">{copy.open}</span>
              <h1>{copy.openTitle}</h1>
              <p>{copy.openHelp}</p>
            </div>
            <label className="field">
              <span>{copy.familyId}</span>
              <input
                autoComplete="off"
                required
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                value={familyId}
                onChange={(event) => setFamilyId(event.target.value)}
              />
            </label>
            <button className="button primary large" type="submit">
              {copy.openButton}
            </button>
          </form>
        )}
        <div className="entry-preferences">
          <label className="compact-control">
            <span>Idioma</span>
            <select value={locale} onChange={(event) => setLocale(event.target.value as Locale)}>
              <option value="pt-PT">PT</option>
              <option value="en">EN</option>
            </select>
          </label>
          <label className="compact-control">
            <span>Aparência</span>
            <select
              value={appearance}
              onChange={(event) => setAppearance(event.target.value as Appearance)}
            >
              <option value="system">Sistema</option>
              <option value="light">Claro</option>
              <option value="dark">Escuro</option>
            </select>
          </label>
        </div>
      </div>
    </main>
  );
}
