import { useState, type FormEvent } from "react";

import { ApiError } from "./api/client";
import { discoverRestaurants } from "./api/restaurantDiscoveryClient";
import type { RestaurantDiscovery } from "./api/restaurantDiscoveryTypes";
import { useI18n } from "./i18n";
import "./restaurant-discovery.css";

const COPY = {
  "pt-PT": {
    eyebrow: "Casa · Restaurantes",
    title: "Restaurantes na área",
    help: "Pesquisa restaurantes reais na zona configurada. Esta lista é descoberta de locais; um prato só entra no ranking nutricional quando houver um item de menu concreto com evidência suficiente.",
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
    empty: "Não foram encontrados restaurantes nesta área.",
    error: "Não foi possível pesquisar restaurantes",
    nutritionNote: "Ainda não classificado nutricionalmente",
  },
  en: {
    eyebrow: "Home base · Restaurants",
    title: "Restaurants in the area",
    help: "Find real restaurants in the configured area. This is place discovery; a dish only enters nutritional ranking when a concrete menu item has sufficient evidence.",
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
    empty: "No restaurants were found in this area.",
    error: "Restaurant search failed",
    nutritionNote: "Not yet nutritionally ranked",
  },
} as const;

function errorText(error: unknown): string {
  if (error instanceof ApiError) return `${error.message} (HTTP ${error.status})`;
  return error instanceof Error ? error.message : String(error);
}

export default function RestaurantDiscoveryScreen({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [area, setArea] = useState("");
  const [discovery, setDiscovery] = useState<RestaurantDiscovery | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setDiscovery(await discoverRestaurants(familyId, area));
    } catch (caught: unknown) {
      setDiscovery(null);
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="restaurant-discovery-screen">
      <header className="screen-header compact-screen-header">
        <div>
          <span className="eyebrow">{copy.eyebrow}</span>
          <h1>{copy.title}</h1>
          <p>{copy.help}</p>
        </div>
      </header>

      <form className="restaurant-search-card" onSubmit={submit}>
        <label className="field">
          <span>{copy.area}</span>
          <input
            maxLength={255}
            placeholder={copy.areaPlaceholder}
            value={area}
            onChange={(event) => setArea(event.target.value)}
          />
          <small>{copy.areaHelp}</small>
        </label>
        <button className="button primary" disabled={busy} type="submit">
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
              </p>
            </div>
            <small>{discovery.attribution}</small>
          </div>
          {discovery.restaurants.length === 0 ? (
            <div className="empty-state compact-empty-state"><p>{copy.empty}</p></div>
          ) : (
            <div className="restaurant-grid">
              {discovery.restaurants.map((restaurant) => (
                <article className="restaurant-card" key={restaurant.provider_place_id}>
                  <div className="restaurant-card__heading">
                    <div>
                      <h3>{restaurant.name}</h3>
                      <span>{copy.nutritionNote}</span>
                    </div>
                    <span className="restaurant-kind">{restaurant.amenity.replace("_", " ")}</span>
                  </div>
                  {restaurant.address ? <p>{restaurant.address}</p> : null}
                  {restaurant.cuisine.length > 0 ? (
                    <p><strong>{copy.cuisine}:</strong> {restaurant.cuisine.join(" · ")}</p>
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
              ))}
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}
