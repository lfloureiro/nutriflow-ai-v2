import { useEffect, useState, type FormEvent } from "react";

import { ApiError } from "./api/client";
import { syncRestaurantMenus } from "./api/restaurantDiscoveryClient";
import type {
  RestaurantMenuItem,
  RestaurantMenuSync,
} from "./api/restaurantDiscoveryTypes";
import { getMealDiscoveryCapabilities } from "./api/setupClient";
import type { MealDiscoveryCapability } from "./api/setupTypes";
import { useI18n } from "./i18n";
import "./restaurant-discovery.css";

const COPY = {
  "pt-PT": {
    eyebrow: "Casa · Restaurantes",
    title: "Restaurantes e ementas",
    help: "Descobre restaurantes, lê as ementas publicadas nos respetivos sites oficiais e guarda os pratos que podem entrar nas recomendações.",
    area: "Área",
    areaPlaceholder: "Ex.: Benfica, Lisboa",
    areaHelp: "Deixa vazio para usar a área definida na família.",
    search: "Atualizar restaurantes e ementas",
    searching: "A procurar restaurantes e ementas…",
    sourceGoogle: "Google",
    sourceOsm: "OpenStreetMap",
    restaurants: "restaurantes analisados",
    dishes: "pratos encontrados",
    ready: "pratos com nutrição utilizável",
    noMenu: "Não foi possível obter uma ementa estruturada deste restaurante.",
    noItems: "Não foram encontrados pratos utilizáveis na ementa.",
    error: "Não foi possível atualizar restaurantes e ementas",
    providerUnavailable: "A descoberta ou leitura das ementas não respondeu. Tenta novamente mais tarde.",
    capabilityGoogle: "Google ativo · os mesmos restaurantes alimentam a sincronização das ementas e as recomendações",
    capabilityFallback: "Google não está configurado · OpenStreetMap é usado apenas como fonte alternativa nesta instalação",
    capabilityNeedsArea: "Falta definir a área padrão da família. Podes configurá-la em Mais ou escrever uma área nesta pesquisa.",
    capabilityDisabled: "A pesquisa de restaurantes está desativada nesta instalação.",
    capabilityUnknown: "Não foi possível confirmar agora o estado da integração.",
    official: "kcal publicadas",
    estimated: "estimativa NutriFlow",
    provider: "nutrição do fornecedor",
    nutritionMissing: "sem dados nutricionais suficientes",
    rankable: "pode entrar na recomendação",
    notRankable: "ainda não entra no ranking nutricional",
    menuSource: "Ver fonte da ementa",
  },
  en: {
    eyebrow: "Home base · Restaurants",
    title: "Restaurants and menus",
    help: "Discover restaurants, read menus published on their official websites and retain dishes that can enter meal recommendations.",
    area: "Area",
    areaPlaceholder: "E.g. Benfica, Lisbon",
    areaHelp: "Leave empty to use the Family's configured area.",
    search: "Refresh restaurants and menus",
    searching: "Finding restaurants and menus…",
    sourceGoogle: "Google",
    sourceOsm: "OpenStreetMap",
    restaurants: "restaurants analysed",
    dishes: "dishes found",
    ready: "dishes with usable nutrition",
    noMenu: "A structured menu could not be obtained for this restaurant.",
    noItems: "No usable dishes were found in this menu.",
    error: "Restaurants and menus could not be refreshed",
    providerUnavailable: "Restaurant discovery or menu reading did not respond. Try again later.",
    capabilityGoogle: "Google active · the same restaurant catalogue feeds menu synchronization and recommendations",
    capabilityFallback: "Google is not configured · OpenStreetMap is used only as this installation's fallback source",
    capabilityNeedsArea: "The Family has no default restaurant area. Configure it in More or enter an area here.",
    capabilityDisabled: "Restaurant discovery is disabled in this installation.",
    capabilityUnknown: "The integration status could not be confirmed right now.",
    official: "published kcal",
    estimated: "NutriFlow estimate",
    provider: "provider nutrition",
    nutritionMissing: "insufficient nutrition data",
    rankable: "eligible for recommendation",
    notRankable: "not yet nutrition-rankable",
    menuSource: "Open menu source",
  },
} as const;

function errorText(error: unknown, locale: "pt-PT" | "en"): string {
  if (error instanceof ApiError) {
    if (error.status === 503) return COPY[locale].providerUnavailable;
    return `${error.message} (HTTP ${error.status})`;
  }
  return error instanceof Error ? error.message : String(error);
}

export function restaurantCapabilityMessage(
  capability: MealDiscoveryCapability | null,
  locale: "pt-PT" | "en",
): string {
  const copy = COPY[locale];
  if (capability === null) return copy.capabilityUnknown;
  if (capability.status === "disabled") return copy.capabilityDisabled;
  if (capability.status === "needs_configuration") return copy.capabilityNeedsArea;
  return capability.credentials_configured ? copy.capabilityGoogle : copy.capabilityFallback;
}

function providerLabel(provider: string, locale: "pt-PT" | "en"): string {
  return provider === "google_places" || provider === "google_maps_apify"
    ? COPY[locale].sourceGoogle
    : COPY[locale].sourceOsm;
}

function evidenceLabel(item: RestaurantMenuItem, locale: "pt-PT" | "en"): string {
  const copy = COPY[locale];
  if (item.nutrition_evidence_level === "official") return copy.official;
  if (item.nutrition_evidence_level === "provider") return copy.provider;
  if (item.nutrition_evidence_level === "estimated") return copy.estimated;
  return copy.nutritionMissing;
}

function formatMoney(value: string | null, currency: string, locale: "pt-PT" | "en") {
  if (value === null) return null;
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return `${value} ${currency}`;
  return new Intl.NumberFormat(locale, { style: "currency", currency }).format(numeric);
}

export default function RestaurantDiscoveryScreen({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [area, setArea] = useState("");
  const [result, setResult] = useState<RestaurantMenuSync | null>(null);
  const [capability, setCapability] = useState<MealDiscoveryCapability | null>(null);
  const [capabilityLoaded, setCapabilityLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setCapabilityLoaded(false);
    void getMealDiscoveryCapabilities(familyId)
      .then((loaded) => {
        if (cancelled) return;
        setCapability(loaded.capabilities.find((item) => item.source === "restaurants") ?? null);
      })
      .catch(() => {
        if (!cancelled) setCapability(null);
      })
      .finally(() => {
        if (!cancelled) setCapabilityLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [familyId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setResult(
        await syncRestaurantMenus(familyId, {
          area: area.trim() || null,
          restaurant_limit: 8,
          item_limit_per_restaurant: 60,
        }),
      );
    } catch (caught: unknown) {
      setResult(null);
      setError(errorText(caught, locale));
    } finally {
      setBusy(false);
    }
  }

  const searchDisabled = busy || (capabilityLoaded && capability?.status === "disabled");
  const totalItems = result?.menus.reduce((sum, menu) => sum + menu.items.length, 0) ?? 0;

  return (
    <div className="restaurant-discovery-screen">
      <header className="screen-header compact-screen-header">
        <div>
          <span className="eyebrow">{copy.eyebrow}</span>
          <h1>{copy.title}</h1>
          <p>{copy.help}</p>
        </div>
      </header>

      {capabilityLoaded ? (
        <div className={`restaurant-capability status-${capability?.status ?? "unknown"}`}>
          <span aria-hidden="true" className="restaurant-capability__dot" />
          <span>{restaurantCapabilityMessage(capability, locale)}</span>
        </div>
      ) : null}

      <form className="restaurant-search-card" onSubmit={submit}>
        <label className="field">
          <span>{copy.area}</span>
          <input
            disabled={capabilityLoaded && capability?.status === "disabled"}
            maxLength={255}
            placeholder={copy.areaPlaceholder}
            value={area}
            onChange={(event) => setArea(event.target.value)}
          />
          <small>{copy.areaHelp}</small>
        </label>
        <button className="button primary" disabled={searchDisabled} type="submit">
          {busy ? copy.searching : copy.search}
        </button>
      </form>

      {error ? (
        <div className="error-banner" role="alert">
          <strong>{copy.error}</strong>
          <span>{error}</span>
        </div>
      ) : null}

      {result ? (
        <section className="restaurant-results">
          <div className="restaurant-results__heading">
            <div>
              <h2>{result.area}</h2>
              <p>
                {providerLabel(result.provider, locale)} · {result.menus.length} {copy.restaurants}
                {" · "}{totalItems} {copy.dishes}
                {" · "}{result.nutrition_ready_item_count} {copy.ready}
              </p>
            </div>
          </div>

          <div className="restaurant-grid">
            {result.menus.map((menu) => (
              <article className="restaurant-card" key={menu.restaurant.provider_place_id}>
                <div className="restaurant-card__heading">
                  <div>
                    <h3>{menu.restaurant.name}</h3>
                    {menu.restaurant.rating ? (
                      <span>
                        ★ {Number(menu.restaurant.rating).toLocaleString(locale, {
                          minimumFractionDigits: 1,
                          maximumFractionDigits: 1,
                        })}
                        {menu.restaurant.rating_count !== null
                          ? ` · ${new Intl.NumberFormat(locale).format(menu.restaurant.rating_count)}`
                          : ""}
                      </span>
                    ) : null}
                  </div>
                </div>
                {menu.restaurant.address ? <p>{menu.restaurant.address}</p> : null}
                {menu.error ? <p className="muted">{menu.error || copy.noMenu}</p> : null}
                {!menu.error && menu.items.length === 0 ? <p className="muted">{copy.noItems}</p> : null}
                {menu.items.length > 0 ? (
                  <div className="restaurant-menu-list">
                    {menu.items.map((item) => (
                      <div
                        className={`restaurant-menu-item ${item.eligible_for_nutrition_ranking ? "is-ready" : ""}`}
                        key={`${item.source_reference}:${item.item_name}:${item.item_price ?? "-"}`}
                      >
                        <div>
                          <strong>{item.item_name}</strong>
                          {item.description ? <small>{item.description}</small> : null}
                          <small>
                            {evidenceLabel(item, locale)} · {item.eligible_for_nutrition_ranking ? copy.rankable : copy.notRankable}
                          </small>
                        </div>
                        <div className="restaurant-menu-item__numbers">
                          {item.energy_kcal !== null ? <strong>{Math.round(Number(item.energy_kcal))} kcal</strong> : null}
                          {item.item_price !== null ? <span>{formatMoney(item.item_price, item.currency, locale)}</span> : null}
                        </div>
                        <a href={item.source_reference} rel="noreferrer" target="_blank">
                          {copy.menuSource}
                        </a>
                      </div>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
