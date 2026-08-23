import { useEffect, useState, type FormEvent } from "react";

import { ApiError } from "./api/client";
import { getFamily, updateFamily } from "./api/setupClient";
import type { MealDiscoverySource } from "./api/setupTypes";
import { useI18n } from "./i18n";
import MealDiscoveryCapabilitySummary from "./MealDiscoveryCapabilitySummary";
import PersonMealDiscoveryOverrides from "./PersonMealDiscoveryOverrides";
import "./meal-discovery-settings.css";

const SOURCES: MealDiscoverySource[] = [
  "shared_recipes",
  "uber_eats",
  "glovo",
  "bolt_food",
  "restaurants",
];

const COPY = {
  "pt-PT": {
    eyebrow: "Casa · Fontes",
    title: "Onde procurar refeições",
    help: "Define as fontes padrão da família. Cada pessoa pode herdar estas opções ou ter um override próprio.",
    shared_recipes: "Receitas partilhadas",
    shared_recipesHelp: "Catálogo NutriFlow e receitas próprias da família.",
    uber_eats: "Uber Eats",
    uber_eatsHelp: "Só produz resultados live quando a integração oficial estiver configurada.",
    glovo: "Glovo",
    glovoHelp: "Só produz resultados live quando a integração oficial estiver configurada.",
    bolt_food: "Bolt Food",
    bolt_foodHelp: "Só produz resultados live quando existir uma integração de consumidor autorizada.",
    restaurants: "Restaurantes na área",
    restaurantsHelp: "Descoberta live de restaurantes; pratos só entram no score com dados de menu suficientes.",
    deliveryAddress: "Morada de entrega",
    restaurantArea: "Área de restaurantes",
    deliveryPlaceholder: "Ex.: Av. do Colégio Militar 37, Lisboa",
    restaurantPlaceholder: "Ex.: Benfica, Lisboa",
    save: "Guardar fontes",
    saving: "A guardar…",
    saved: "Fontes atualizadas",
    loading: "A carregar configuração…",
    error: "Não foi possível guardar a configuração",
    sourceRequired: "Seleciona pelo menos uma fonte.",
    deliveryRequired: "Indica a morada de entrega para os providers selecionados.",
    areaRequired: "Indica a área onde procurar restaurantes.",
  },
  en: {
    eyebrow: "Home base · Sources",
    title: "Where to find meals",
    help: "Set the Family defaults. Each Person can inherit these options or keep a separate override.",
    shared_recipes: "Shared recipes",
    shared_recipesHelp: "NutriFlow catalogue and the Family's own recipes.",
    uber_eats: "Uber Eats",
    uber_eatsHelp: "Returns live results only when the official integration is configured.",
    glovo: "Glovo",
    glovoHelp: "Returns live results only when the official integration is configured.",
    bolt_food: "Bolt Food",
    bolt_foodHelp: "Returns live results only when an authorized consumer integration is available.",
    restaurants: "Restaurants in the area",
    restaurantsHelp: "Live restaurant discovery; dishes only enter scoring with sufficient menu evidence.",
    deliveryAddress: "Delivery address",
    restaurantArea: "Restaurant area",
    deliveryPlaceholder: "E.g. 37 Av. do Colégio Militar, Lisbon",
    restaurantPlaceholder: "E.g. Benfica, Lisbon",
    save: "Save sources",
    saving: "Saving…",
    saved: "Sources updated",
    loading: "Loading settings…",
    error: "Could not save settings",
    sourceRequired: "Select at least one source.",
    deliveryRequired: "Enter a delivery address for the selected providers.",
    areaRequired: "Enter the area where restaurants should be found.",
  },
} as const;

function errorText(error: unknown): string {
  if (error instanceof ApiError) return `${error.message} (HTTP ${error.status})`;
  return error instanceof Error ? error.message : String(error);
}

function isDeliverySource(source: MealDiscoverySource): boolean {
  return source === "uber_eats" || source === "glovo" || source === "bolt_food";
}

export default function MealDiscoverySettings({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [sources, setSources] = useState<MealDiscoverySource[]>([]);
  const [deliveryAddress, setDeliveryAddress] = useState("");
  const [restaurantArea, setRestaurantArea] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void getFamily(familyId)
      .then((family) => {
        if (cancelled) return;
        setSources(family.meal_discovery_sources);
        setDeliveryAddress(family.delivery_address ?? "");
        setRestaurantArea(family.restaurant_area ?? "");
      })
      .catch((caught: unknown) => {
        if (!cancelled) setError(errorText(caught));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [familyId]);

  function toggleSource(source: MealDiscoverySource) {
    setSaved(false);
    setSources((current) =>
      current.includes(source)
        ? current.filter((value) => value !== source)
        : [...current, source],
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSaved(false);
    if (sources.length === 0) {
      setError(copy.sourceRequired);
      return;
    }
    const wantsDelivery = sources.some(isDeliverySource);
    if (wantsDelivery && !deliveryAddress.trim()) {
      setError(copy.deliveryRequired);
      return;
    }
    if (sources.includes("restaurants") && !restaurantArea.trim()) {
      setError(copy.areaRequired);
      return;
    }

    setBusy(true);
    try {
      const updated = await updateFamily(familyId, {
        meal_discovery_sources: sources,
        delivery_address: deliveryAddress.trim() || null,
        restaurant_area: restaurantArea.trim() || null,
      });
      setSources(updated.meal_discovery_sources);
      setDeliveryAddress(updated.delivery_address ?? "");
      setRestaurantArea(updated.restaurant_area ?? "");
      setSaved(true);
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="shell-loading">{copy.loading}</div>;

  return (
    <div className="meal-discovery-settings">
      <header className="screen-header compact-screen-header">
        <div>
          <span className="eyebrow">{copy.eyebrow}</span>
          <h1>{copy.title}</h1>
          <p>{copy.help}</p>
        </div>
      </header>

      <MealDiscoveryCapabilitySummary familyId={familyId} />

      {error ? <div className="error-banner" role="alert"><strong>{copy.error}</strong><span>{error}</span></div> : null}
      {saved ? <div className="decision-result" role="status"><strong>{copy.saved}</strong></div> : null}

      <form className="meal-source-settings-card" onSubmit={submit}>
        <div className="meal-source-settings-grid">
          {SOURCES.map((source) => (
            <label className={`meal-source-setting ${sources.includes(source) ? "selected" : ""}`} key={source}>
              <input
                checked={sources.includes(source)}
                onChange={() => toggleSource(source)}
                type="checkbox"
              />
              <span>
                <strong>{copy[source]}</strong>
                <small>{copy[`${source}Help` as keyof typeof copy]}</small>
              </span>
            </label>
          ))}
        </div>

        {sources.some(isDeliverySource) ? (
          <label className="field">
            <span>{copy.deliveryAddress}</span>
            <input
              maxLength={500}
              placeholder={copy.deliveryPlaceholder}
              value={deliveryAddress}
              onChange={(event) => setDeliveryAddress(event.target.value)}
            />
          </label>
        ) : null}

        {sources.includes("restaurants") ? (
          <label className="field">
            <span>{copy.restaurantArea}</span>
            <input
              maxLength={255}
              placeholder={copy.restaurantPlaceholder}
              value={restaurantArea}
              onChange={(event) => setRestaurantArea(event.target.value)}
            />
          </label>
        ) : null}

        <button className="button primary" disabled={busy} type="submit">
          {busy ? copy.saving : copy.save}
        </button>
      </form>

      <PersonMealDiscoveryOverrides familyId={familyId} />
    </div>
  );
}
