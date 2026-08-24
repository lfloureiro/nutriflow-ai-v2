import { useEffect, useState, type FormEvent } from "react";

import { ApiError } from "./api/client";
import { discoverRestaurants } from "./api/restaurantDiscoveryClient";
import type {
  RestaurantDiscovery,
  RestaurantDiscoveryPlace,
} from "./api/restaurantDiscoveryTypes";
import { getMealDiscoveryCapabilities } from "./api/setupClient";
import type { MealDiscoveryCapability } from "./api/setupTypes";
import { useI18n } from "./i18n";
import "./restaurant-discovery.css";

const COPY = {
  "pt-PT": {
    eyebrow: "Casa · Restaurantes",
    title: "Restaurantes na área",
    help: "Descobre restaurantes e ordena-os com sinais de qualidade quando estão disponíveis. A nutrição continua a ser avaliada ao nível do prato concreto, não do restaurante inteiro.",
    area: "Área",
    areaPlaceholder: "Ex.: Benfica, Lisboa",
    areaHelp: "Deixa vazio para usar a área definida na família.",
    search: "Procurar restaurantes",
    searching: "A procurar…",
    results: "restaurantes encontrados",
    cached: "cache",
    live: "pesquisa live",
    cuisine: "Cozinha",
    opening: "Horário",
    website: "Site / menu",
    source: "Fonte",
    sourceGoogle: "Google Places",
    sourceOsm: "OpenStreetMap",
    sourceOsmFallback: "OpenStreetMap · fallback",
    empty: "Não foram encontrados restaurantes nesta área.",
    error: "Não foi possível pesquisar restaurantes",
    providerUnavailable: "Os serviços externos de descoberta não responderam. Tenta novamente mais tarde.",
    capabilityGoogle: "Google Places ativo · ranking por qualidade · OpenStreetMap como fallback",
    capabilityFallback: "OpenStreetMap ativo como fallback · falta configurar Google Places para melhorar o ranking",
    capabilityNeedsArea: "Falta definir a área padrão da família. Podes configurá-la em Mais ou escrever uma área nesta pesquisa.",
    capabilityDisabled: "A pesquisa live de restaurantes está desativada nesta instalação.",
    capabilityUnknown: "Não foi possível confirmar agora o estado da integração. A pesquisa continua disponível para teste.",
    nutritionNote: "Nutrição pendente do prato/menu",
    ratings: "avaliações",
    lunch: "Almoço",
    dinner: "Jantar",
    delivery: "Entrega",
    takeout: "Take-away",
    dineIn: "No local",
    vegetarian: "Opções vegetarianas",
    priceFree: "Grátis",
    priceInexpensive: "€",
    priceModerate: "€€",
    priceExpensive: "€€€",
    priceVeryExpensive: "€€€€",
  },
  en: {
    eyebrow: "Home base · Restaurants",
    title: "Restaurants in the area",
    help: "Discover restaurants and rank them with quality signals when available. Nutrition is still evaluated for a concrete dish, not for an entire restaurant.",
    area: "Area",
    areaPlaceholder: "E.g. Benfica, Lisbon",
    areaHelp: "Leave empty to use the Family's configured area.",
    search: "Find restaurants",
    searching: "Searching…",
    results: "restaurants found",
    cached: "cache",
    live: "live search",
    cuisine: "Cuisine",
    opening: "Opening hours",
    website: "Website / menu",
    source: "Source",
    sourceGoogle: "Google Places",
    sourceOsm: "OpenStreetMap",
    sourceOsmFallback: "OpenStreetMap · fallback",
    empty: "No restaurants were found in this area.",
    error: "Restaurant search failed",
    providerUnavailable: "External restaurant-discovery services did not respond. Try again later.",
    capabilityGoogle: "Google Places active · quality ranking · OpenStreetMap fallback",
    capabilityFallback: "OpenStreetMap fallback active · configure Google Places to improve ranking",
    capabilityNeedsArea: "The Family has no default restaurant area. Configure it in More or enter an area for this search.",
    capabilityDisabled: "Live restaurant discovery is disabled in this installation.",
    capabilityUnknown: "The integration status could not be confirmed right now. Search remains available for testing.",
    nutritionNote: "Nutrition pending concrete dish/menu evidence",
    ratings: "ratings",
    lunch: "Lunch",
    dinner: "Dinner",
    delivery: "Delivery",
    takeout: "Take-away",
    dineIn: "Dine-in",
    vegetarian: "Vegetarian options",
    priceFree: "Free",
    priceInexpensive: "$",
    priceModerate: "$$",
    priceExpensive: "$$$",
    priceVeryExpensive: "$$$$",
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
  const copy = COPY[locale];
  if (provider === "google_places") return copy.sourceGoogle;
  if (provider === "openstreetmap_fallback") return copy.sourceOsmFallback;
  return copy.sourceOsm;
}

function priceLabel(priceLevel: string | null, locale: "pt-PT" | "en"): string | null {
  const copy = COPY[locale];
  const labels: Record<string, string> = {
    PRICE_LEVEL_FREE: copy.priceFree,
    PRICE_LEVEL_INEXPENSIVE: copy.priceInexpensive,
    PRICE_LEVEL_MODERATE: copy.priceModerate,
    PRICE_LEVEL_EXPENSIVE: copy.priceExpensive,
    PRICE_LEVEL_VERY_EXPENSIVE: copy.priceVeryExpensive,
  };
  return priceLevel ? labels[priceLevel] ?? null : null;
}

function serviceLabels(
  restaurant: RestaurantDiscoveryPlace,
  locale: "pt-PT" | "en",
): string[] {
  const copy = COPY[locale];
  const labels: Array<string | null> = [
    restaurant.serves_lunch ? copy.lunch : null,
    restaurant.serves_dinner ? copy.dinner : null,
    restaurant.delivery ? copy.delivery : null,
    restaurant.takeout ? copy.takeout : null,
    restaurant.dine_in ? copy.dineIn : null,
    restaurant.serves_vegetarian_food ? copy.vegetarian : null,
  ];
  return labels.filter((value): value is string => value !== null);
}

export default function RestaurantDiscoveryScreen({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [area, setArea] = useState("");
  const [discovery, setDiscovery] = useState<RestaurantDiscovery | null>(null);
  const [capability, setCapability] = useState<MealDiscoveryCapability | null>(null);
  const [capabilityLoaded, setCapabilityLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setCapabilityLoaded(false);
    void getMealDiscoveryCapabilities(familyId)
      .then((result) => {
        if (cancelled) return;
        setCapability(
          result.capabilities.find((item) => item.source === "restaurants") ?? null,
        );
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
      setDiscovery(await discoverRestaurants(familyId, area));
    } catch (caught: unknown) {
      setDiscovery(null);
      setError(errorText(caught, locale));
    } finally {
      setBusy(false);
    }
  }

  const searchDisabled = busy || (capabilityLoaded && capability?.status === "disabled");
  const capabilityState = capability?.status === "ready" ? "ready" : capability?.status ?? "unknown";

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
        <div className={`restaurant-capability status-${capabilityState}`}>
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

      {discovery ? (
        <section className="restaurant-results">
          <div className="restaurant-results__heading">
            <div>
              <h2>{discovery.area}</h2>
              <p>
                {discovery.restaurants.length} {copy.results} · {discovery.cached ? copy.cached : copy.live}
                {" · "}{providerLabel(discovery.provider, locale)}
              </p>
            </div>
            <small>{discovery.attribution}</small>
          </div>
          {discovery.restaurants.length === 0 ? (
            <div className="empty-state compact-empty-state"><p>{copy.empty}</p></div>
          ) : (
            <div className="restaurant-grid">
              {discovery.restaurants.map((restaurant) => {
                const services = serviceLabels(restaurant, locale);
                const price = priceLabel(restaurant.price_level, locale);
                return (
                  <article className="restaurant-card" key={restaurant.provider_place_id}>
                    <div className="restaurant-card__heading">
                      <div>
                        <h3>{restaurant.name}</h3>
                        <span>{copy.nutritionNote}</span>
                      </div>
                      <span className="restaurant-kind">
                        {(restaurant.primary_type ?? restaurant.amenity).replaceAll("_", " ")}
                      </span>
                    </div>
                    <div className="restaurant-quality-row">
                      {restaurant.rating ? (
                        <strong>
                          ★ {Number(restaurant.rating).toLocaleString(locale, {
                            maximumFractionDigits: 1,
                            minimumFractionDigits: 1,
                          })}
                        </strong>
                      ) : null}
                      {restaurant.rating_count !== null ? (
                        <span>
                          {new Intl.NumberFormat(locale).format(restaurant.rating_count)} {copy.ratings}
                        </span>
                      ) : null}
                      {price ? <span className="restaurant-price">{price}</span> : null}
                    </div>
                    {restaurant.address ? <p>{restaurant.address}</p> : null}
                    {restaurant.cuisine.length > 0 ? (
                      <p><strong>{copy.cuisine}:</strong> {restaurant.cuisine.join(" · ")}</p>
                    ) : null}
                    {services.length > 0 ? (
                      <div className="restaurant-service-row">
                        {services.map((service) => <span key={service}>{service}</span>)}
                      </div>
                    ) : null}
                    {restaurant.opening_hours ? (
                      <p><strong>{copy.opening}:</strong> {restaurant.opening_hours}</p>
                    ) : null}
                    <div className="restaurant-links">
                      {restaurant.website ? (
                        <a href={restaurant.website} rel="noreferrer" target="_blank">{copy.website}</a>
                      ) : null}
                      <a href={restaurant.source_reference} rel="noreferrer" target="_blank">{copy.source}</a>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}
