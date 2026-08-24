import { useEffect, useMemo, useState, type FormEvent } from "react";

import { ApiError } from "./api/client";
import { syncMealDeliveryProvider } from "./api/mealDeliveryClient";
import type {
  MealDeliveryMenuItem,
  MealDeliveryProviderKey,
} from "./api/mealDeliveryTypes";
import { getMealDiscoveryCapabilities } from "./api/setupClient";
import type { MealDiscoveryCapability } from "./api/setupTypes";
import { useI18n } from "./i18n";

const PROVIDERS: MealDeliveryProviderKey[] = ["uber_eats", "glovo", "bolt_food"];

const COPY = {
  "pt-PT": {
    eyebrow: "Casa · Menus de entrega",
    title: "Pratos disponíveis para entrega",
    help: "Consulta pratos reais devolvidos pelos providers autorizados. Só entram no ranking nutricional quando existe evidência de nutrição suficiente.",
    uber_eats: "Uber Eats",
    glovo: "Glovo",
    bolt_food: "Bolt Food",
    selected: "Ativo na família",
    notSelected: "Não ativo na família",
    available: "Integração disponível",
    integrationRequired: "Integração ainda necessária",
    configureSource: "Ativa esta fonte em Mais → Dados da família antes de sincronizar.",
    missingCredentials: "Faltam credenciais ou aprovação do provider para pesquisa consumer.",
    missingAccess: "As credenciais existem, mas o acesso consumer ainda não está aprovado/ativado.",
    missingAdapter: "O acesso está configurado, mas falta o adapter executável desta instalação.",
    unavailable: "Este provider não expõe atualmente uma API pública de descoberta consumer utilizável pelo NutriFlow.",
    search: "Pesquisar no menu",
    searchPlaceholder: "Ex.: frango, massa, poke…",
    sync: "Atualizar pratos",
    syncing: "A atualizar…",
    results: "pratos observados",
    empty: "O provider não devolveu pratos para esta pesquisa.",
    noResults: "Ainda não foi feita uma pesquisa neste provider.",
    error: "Não foi possível atualizar o menu",
    restaurant: "Restaurante",
    price: "Preço",
    nutrition: "Nutrição",
    eligible: "Elegível para ranking",
    notEligible: "Nutrição insuficiente",
    evidenceOfficial: "oficial",
    evidenceProvider: "provider",
    evidenceEstimated: "estimada",
    source: "Abrir fonte",
    kcal: "kcal",
  },
  en: {
    eyebrow: "Home base · Delivery menus",
    title: "Dishes available for delivery",
    help: "Browse real dishes returned by authorized providers. Items only enter nutritional ranking when sufficient nutrition evidence exists.",
    uber_eats: "Uber Eats",
    glovo: "Glovo",
    bolt_food: "Bolt Food",
    selected: "Enabled for Family",
    notSelected: "Not enabled for Family",
    available: "Integration available",
    integrationRequired: "Integration still required",
    configureSource: "Enable this source in More → Family details before synchronizing.",
    missingCredentials: "Provider credentials or consumer-search approval are missing.",
    missingAccess: "Credentials exist, but consumer access is not yet approved/enabled.",
    missingAdapter: "Access is configured, but this installation has no executable adapter yet.",
    unavailable: "This provider does not currently expose a public consumer-discovery API usable by NutriFlow.",
    search: "Search menu",
    searchPlaceholder: "E.g. chicken, pasta, poke…",
    sync: "Refresh dishes",
    syncing: "Refreshing…",
    results: "observed dishes",
    empty: "The provider returned no dishes for this search.",
    noResults: "No search has been run for this provider yet.",
    error: "The delivery menu could not be refreshed",
    restaurant: "Restaurant",
    price: "Price",
    nutrition: "Nutrition",
    eligible: "Eligible for ranking",
    notEligible: "Insufficient nutrition",
    evidenceOfficial: "official",
    evidenceProvider: "provider",
    evidenceEstimated: "estimated",
    source: "Open source",
    kcal: "kcal",
  },
} as const;

function errorText(error: unknown): string {
  if (error instanceof ApiError) return `${error.message} (HTTP ${error.status})`;
  return error instanceof Error ? error.message : String(error);
}

function capabilityReason(
  capability: MealDiscoveryCapability | null,
  locale: "pt-PT" | "en",
): string {
  const copy = COPY[locale];
  if (capability === null) return copy.integrationRequired;
  if (!capability.selected) return copy.configureSource;
  if (capability.live) return copy.available;
  if (capability.credentials_configured === false) return copy.missingCredentials;
  if (capability.access_enabled === false) return copy.missingAccess;
  if (capability.adapter_available === false && capability.credentials_configured) {
    return copy.missingAdapter;
  }
  return copy.unavailable;
}

function price(item: MealDeliveryMenuItem, locale: "pt-PT" | "en"): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: item.currency,
  }).format(Number(item.item_price));
}

function nutritionLabel(
  item: MealDeliveryMenuItem,
  locale: "pt-PT" | "en",
): string {
  const copy = COPY[locale];
  if (item.energy_kcal === null) return copy.notEligible;
  const evidence =
    item.nutrition_evidence_level === "official"
      ? copy.evidenceOfficial
      : item.nutrition_evidence_level === "provider"
        ? copy.evidenceProvider
        : copy.evidenceEstimated;
  const energy = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(
    Number(item.energy_kcal),
  );
  return `${energy} ${copy.kcal} · ${evidence}`;
}

export default function DeliveryMenuScreen({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [provider, setProvider] = useState<MealDeliveryProviderKey>("uber_eats");
  const [capabilities, setCapabilities] = useState<MealDiscoveryCapability[]>([]);
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<MealDeliveryMenuItem[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void getMealDiscoveryCapabilities(familyId)
      .then((result) => {
        if (!cancelled) setCapabilities(result.capabilities);
      })
      .catch(() => {
        if (!cancelled) setCapabilities([]);
      });
    return () => {
      cancelled = true;
    };
  }, [familyId]);

  useEffect(() => {
    setItems(null);
    setError(null);
  }, [provider]);

  const capability = useMemo(
    () => capabilities.find((item) => item.source === provider) ?? null,
    [capabilities, provider],
  );
  const canSync = Boolean(capability?.selected && capability.live);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!canSync) return;
    setBusy(true);
    setError(null);
    try {
      const result = await syncMealDeliveryProvider(familyId, provider, query);
      setItems(result.items);
    } catch (caught: unknown) {
      setItems(null);
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="delivery-menu-screen">
      <header className="screen-header compact-screen-header">
        <div>
          <span className="eyebrow">{copy.eyebrow}</span>
          <h1>{copy.title}</h1>
          <p>{copy.help}</p>
        </div>
      </header>

      <div className="delivery-provider-tabs" role="tablist">
        {PROVIDERS.map((key) => {
          const itemCapability = capabilities.find((item) => item.source === key);
          return (
            <button
              aria-selected={provider === key}
              className={provider === key ? "active" : ""}
              key={key}
              onClick={() => setProvider(key)}
              role="tab"
              type="button"
            >
              <strong>{copy[key]}</strong>
              <small>
                {itemCapability?.live ? copy.available : copy.integrationRequired}
              </small>
            </button>
          );
        })}
      </div>

      <div className={`delivery-provider-state ${canSync ? "ready" : "pending"}`}>
        <div>
          <strong>{copy[provider]}</strong>
          <span>{capability?.selected ? copy.selected : copy.notSelected}</span>
        </div>
        <p>{capabilityReason(capability, locale)}</p>
      </div>

      <form className="delivery-menu-search" onSubmit={submit}>
        <label className="field">
          <span>{copy.search}</span>
          <input
            disabled={!canSync}
            maxLength={160}
            placeholder={copy.searchPlaceholder}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <button className="button primary" disabled={!canSync || busy} type="submit">
          {busy ? copy.syncing : copy.sync}
        </button>
      </form>

      {error ? (
        <div className="error-banner" role="alert">
          <strong>{copy.error}</strong>
          <span>{error}</span>
        </div>
      ) : null}

      {items === null ? (
        <div className="ingredient-empty">{copy.noResults}</div>
      ) : items.length === 0 ? (
        <div className="ingredient-empty">{copy.empty}</div>
      ) : (
        <section className="delivery-menu-results">
          <div className="delivery-menu-results__heading">
            <strong>{copy[provider]}</strong>
            <span>{items.length} {copy.results}</span>
          </div>
          <div className="delivery-dish-list">
            {items.map((item) => (
              <article
                className="delivery-dish-card"
                key={`${item.merchant_name}:${item.item_name}:${item.item_price}`}
              >
                <div className="delivery-dish-card__heading">
                  <div>
                    <h3>{item.item_name}</h3>
                    <span>{copy.restaurant}: {item.merchant_name}</span>
                  </div>
                  <strong>{price(item, locale)}</strong>
                </div>
                {item.description ? <p>{item.description}</p> : null}
                <div className="delivery-dish-meta">
                  <span>{copy.nutrition}: {nutritionLabel(item, locale)}</span>
                  <span className={item.eligible_for_nutrition_ranking ? "eligible" : "pending"}>
                    {item.eligible_for_nutrition_ranking ? copy.eligible : copy.notEligible}
                  </span>
                </div>
                <a href={item.source_reference} rel="noreferrer" target="_blank">
                  {copy.source}
                </a>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
