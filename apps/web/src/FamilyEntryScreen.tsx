import { useMemo, useState, type FormEvent } from "react";

import { ApiError } from "./api/client";
import { createFamily } from "./api/setupClient";
import type { Family, MealDiscoverySource } from "./api/setupTypes";
import { useI18n, type Locale } from "./i18n";
import { useTheme, type Appearance } from "./theme";
import { supportedTimezones } from "./timezones";

const SOURCE_OPTIONS: MealDiscoverySource[] = [
  "shared_recipes",
  "uber_eats",
  "glovo",
  "restaurants",
];

const COPY = {
  "pt-PT": {
    create: "Criar família",
    open: "Abrir existente",
    createTitle: "Criar o espaço da família",
    createHelp:
      "Começa pela família. Depois adicionas as pessoas e o NutriFlow calcula os objetivos energéticos individuais.",
    familyName: "Nome da família",
    timezone: "Fuso horário",
    sources: "Onde queres procurar refeições?",
    sourcesHelp: "Estas são as opções por defeito da família. Cada pessoa pode ter preferências diferentes mais tarde.",
    shared_recipes: "Receitas partilhadas",
    uber_eats: "Uber Eats",
    glovo: "Glovo",
    restaurants: "Restaurantes na área",
    deliveryAddress: "Morada de entrega",
    deliveryAddressPlaceholder: "Rua, número, localidade…",
    restaurantArea: "Área onde procurar restaurantes",
    restaurantAreaPlaceholder: "Ex.: Benfica, Lisboa ou perto de casa",
    providerNote: "Uber Eats e Glovo só ficam live quando a integração oficial do provider estiver configurada.",
    createButton: "Criar família",
    creating: "A criar…",
    openTitle: "Abrir uma família existente",
    openHelp:
      "Enquanto não existe autenticação, podes continuar a abrir uma família pelo respetivo ID.",
    familyId: "ID da família",
    openButton: "Abrir família",
    sourceRequired: "Escolhe pelo menos uma origem de refeições.",
    deliveryAddressRequired: "Indica uma morada para procurar entregas.",
    restaurantAreaRequired: "Indica a área onde queres procurar restaurantes.",
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
    sources: "Where should meals be discovered?",
    sourcesHelp: "These are the family's defaults. Each person can override them later.",
    shared_recipes: "Shared recipes",
    uber_eats: "Uber Eats",
    glovo: "Glovo",
    restaurants: "Restaurants in the area",
    deliveryAddress: "Delivery address",
    deliveryAddressPlaceholder: "Street, number, city…",
    restaurantArea: "Restaurant search area",
    restaurantAreaPlaceholder: "E.g. Benfica, Lisbon or near home",
    providerNote: "Uber Eats and Glovo become live only when the official provider integration is configured.",
    createButton: "Create family",
    creating: "Creating…",
    openTitle: "Open an existing family",
    openHelp:
      "Until authentication is available, an existing family can still be opened by ID.",
    familyId: "Family ID",
    openButton: "Open family",
    sourceRequired: "Choose at least one meal source.",
    deliveryAddressRequired: "Enter an address for delivery discovery.",
    restaurantAreaRequired: "Enter the area where restaurants should be discovered.",
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
  const [sources, setSources] = useState<MealDiscoverySource[]>(["shared_recipes"]);
  const [deliveryAddress, setDeliveryAddress] = useState("");
  const [restaurantArea, setRestaurantArea] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wantsDelivery = sources.includes("uber_eats") || sources.includes("glovo");
  const wantsRestaurants = sources.includes("restaurants");

  function toggleSource(source: MealDiscoverySource) {
    setSources((current) =>
      current.includes(source)
        ? current.filter((item) => item !== source)
        : [...current, source],
    );
  }

  async function submitCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (sources.length === 0) {
      setError(copy.sourceRequired);
      return;
    }
    if (wantsDelivery && !deliveryAddress.trim()) {
      setError(copy.deliveryAddressRequired);
      return;
    }
    if (wantsRestaurants && !restaurantArea.trim()) {
      setError(copy.restaurantAreaRequired);
      return;
    }
    setBusy(true);
    try {
      const family = await createFamily({
        name: name.trim(),
        timezone,
        meal_discovery_sources: sources,
        delivery_address: deliveryAddress.trim() || null,
        restaurant_area: restaurantArea.trim() || null,
      });
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
          <span className="brand-mark" aria-hidden="true">N</span>
          <strong>NutriFlow AI</strong>
        </div>
        <div className="segmented-control family-entry-mode">
          <button className={mode === "create" ? "active" : ""} onClick={() => setMode("create")} type="button">
            {copy.create}
          </button>
          <button className={mode === "open" ? "active" : ""} onClick={() => setMode("open")} type="button">
            {copy.open}
          </button>
        </div>
        {error || externalError ? (
          <div className="error-banner" role="alert">
            <strong>{copy.error}</strong><span>{error ?? externalError}</span>
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
              <input required maxLength={120} value={name} onChange={(event) => setName(event.target.value)} />
            </label>
            <label className="field">
              <span>{copy.timezone}</span>
              <select required value={timezone} onChange={(event) => setTimezone(event.target.value)}>
                {timezoneOptions.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </label>
            <section className="family-source-setup">
              <div>
                <strong>{copy.sources}</strong>
                <p className="muted compact">{copy.sourcesHelp}</p>
              </div>
              <div className="family-source-grid">
                {SOURCE_OPTIONS.map((source) => (
                  <label className={`recommend-source-card ${sources.includes(source) ? "selected" : ""}`} key={source}>
                    <input checked={sources.includes(source)} onChange={() => toggleSource(source)} type="checkbox" />
                    <span><strong>{copy[source]}</strong></span>
                  </label>
                ))}
              </div>
              {wantsDelivery ? (
                <label className="field">
                  <span>{copy.deliveryAddress}</span>
                  <input required placeholder={copy.deliveryAddressPlaceholder} value={deliveryAddress} onChange={(event) => setDeliveryAddress(event.target.value)} />
                </label>
              ) : null}
              {wantsRestaurants ? (
                <label className="field">
                  <span>{copy.restaurantArea}</span>
                  <input required placeholder={copy.restaurantAreaPlaceholder} value={restaurantArea} onChange={(event) => setRestaurantArea(event.target.value)} />
                </label>
              ) : null}
              {(sources.includes("uber_eats") || sources.includes("glovo")) ? <small className="muted">{copy.providerNote}</small> : null}
            </section>
            <button className="button primary large" disabled={busy} type="submit">{busy ? copy.creating : copy.createButton}</button>
          </form>
        ) : (
          <form className="stack" onSubmit={submitOpen}>
            <div>
              <span className="eyebrow">{copy.open}</span><h1>{copy.openTitle}</h1><p>{copy.openHelp}</p>
            </div>
            <label className="field">
              <span>{copy.familyId}</span>
              <input autoComplete="off" required placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" value={familyId} onChange={(event) => setFamilyId(event.target.value)} />
            </label>
            <button className="button primary large" type="submit">{copy.openButton}</button>
          </form>
        )}
        <div className="entry-preferences">
          <label className="compact-control">
            <span>Idioma</span>
            <select value={locale} onChange={(event) => setLocale(event.target.value as Locale)}>
              <option value="pt-PT">PT</option><option value="en">EN</option>
            </select>
          </label>
          <label className="compact-control">
            <span>Aparência</span>
            <select value={appearance} onChange={(event) => setAppearance(event.target.value as Appearance)}>
              <option value="system">Sistema</option><option value="light">Claro</option><option value="dark">Escuro</option>
            </select>
          </label>
        </div>
      </div>
    </main>
  );
}
