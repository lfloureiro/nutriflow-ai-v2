import { useEffect, useState, type FormEvent } from "react";

import { ApiError } from "./api/client";
import { getFamily, updateFamily } from "./api/setupClient";
import type { Family, MealDiscoverySource } from "./api/setupTypes";
import { useI18n } from "./i18n";

const SOURCES: MealDiscoverySource[] = [
  "shared_recipes",
  "restaurants",
  "uber_eats",
  "glovo",
  "bolt_food",
];

const COPY = {
  "pt-PT": {
    title: "Dados da família",
    help: "Nome, fuso horário e origens usadas para procurar refeições. As pessoas podem ter configurações próprias que substituem estes valores.",
    name: "Nome da família",
    timezone: "Fuso horário",
    deliveryAddress: "Morada para entregas",
    restaurantArea: "Área para restaurantes",
    sources: "Origens de refeições",
    shared_recipes: "Receitas partilhadas",
    restaurants: "Restaurantes",
    uber_eats: "Uber Eats",
    glovo: "Glovo",
    bolt_food: "Bolt Food",
    save: "Guardar família",
    saving: "A guardar…",
    loading: "A carregar dados da família…",
    requiredName: "Indica o nome da família.",
    requiredSource: "Escolhe pelo menos uma origem de refeições.",
    deliveryRequired: "Indica uma morada se ativares um serviço de entrega.",
    areaRequired: "Indica uma área se ativares restaurantes.",
    error: "Não foi possível guardar a família",
  },
  en: {
    title: "Family details",
    help: "Name, timezone and meal-discovery sources. Individual people may override these defaults.",
    name: "Family name",
    timezone: "Timezone",
    deliveryAddress: "Delivery address",
    restaurantArea: "Restaurant area",
    sources: "Meal sources",
    shared_recipes: "Shared recipes",
    restaurants: "Restaurants",
    uber_eats: "Uber Eats",
    glovo: "Glovo",
    bolt_food: "Bolt Food",
    save: "Save family",
    saving: "Saving…",
    loading: "Loading Family details…",
    requiredName: "Enter a Family name.",
    requiredSource: "Choose at least one meal source.",
    deliveryRequired: "Enter a delivery address when a delivery service is enabled.",
    areaRequired: "Enter a restaurant area when restaurants are enabled.",
    error: "The Family could not be saved",
  },
} as const;

function errorText(error: unknown): string {
  if (error instanceof ApiError) return `${error.message} (HTTP ${error.status})`;
  return error instanceof Error ? error.message : String(error);
}

export default function FamilySettings({
  familyId,
  onSaved,
}: {
  familyId: string;
  onSaved: (family: Family) => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [family, setFamily] = useState<Family | null>(null);
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState("Europe/Lisbon");
  const [deliveryAddress, setDeliveryAddress] = useState("");
  const [restaurantArea, setRestaurantArea] = useState("");
  const [sources, setSources] = useState<MealDiscoverySource[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setBusy(true);
    setError(null);
    void getFamily(familyId)
      .then((result) => {
        if (cancelled) return;
        setFamily(result);
        setName(result.name);
        setTimezone(result.timezone);
        setDeliveryAddress(result.delivery_address ?? "");
        setRestaurantArea(result.restaurant_area ?? "");
        setSources(result.meal_discovery_sources);
      })
      .catch((caught: unknown) => {
        if (!cancelled) setError(errorText(caught));
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [familyId]);

  function toggleSource(source: MealDiscoverySource) {
    setSources((current) =>
      current.includes(source)
        ? current.filter((item) => item !== source)
        : [...current, source],
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError(copy.requiredName);
      return;
    }
    if (sources.length === 0) {
      setError(copy.requiredSource);
      return;
    }
    if (sources.some((source) => ["uber_eats", "glovo", "bolt_food"].includes(source)) && !deliveryAddress.trim()) {
      setError(copy.deliveryRequired);
      return;
    }
    if (sources.includes("restaurants") && !restaurantArea.trim()) {
      setError(copy.areaRequired);
      return;
    }

    setBusy(true);
    try {
      const result = await updateFamily(familyId, {
        name: name.trim(),
        timezone: timezone.trim() || "Europe/Lisbon",
        meal_discovery_sources: sources,
        delivery_address: deliveryAddress.trim() || null,
        restaurant_area: restaurantArea.trim() || null,
      });
      setFamily(result);
      onSaved(result);
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  if (busy && family === null) {
    return <div className="shell-loading">{copy.loading}</div>;
  }

  return (
    <section className="settings-card family-settings-card">
      <div className="family-settings-heading">
        <div>
          <h2>{copy.title}</h2>
          <p>{copy.help}</p>
        </div>
      </div>
      {error ? (
        <div className="error-banner" role="alert">
          <strong>{copy.error}</strong>
          <span>{error}</span>
        </div>
      ) : null}
      <form className="family-settings-form" onSubmit={submit}>
        <div className="family-settings-grid">
          <label className="field">
            <span>{copy.name}</span>
            <input value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label className="field">
            <span>{copy.timezone}</span>
            <input value={timezone} onChange={(event) => setTimezone(event.target.value)} />
          </label>
          <label className="field">
            <span>{copy.deliveryAddress}</span>
            <input value={deliveryAddress} onChange={(event) => setDeliveryAddress(event.target.value)} />
          </label>
          <label className="field">
            <span>{copy.restaurantArea}</span>
            <input value={restaurantArea} onChange={(event) => setRestaurantArea(event.target.value)} />
          </label>
        </div>
        <fieldset className="family-source-fieldset">
          <legend>{copy.sources}</legend>
          <div className="family-source-grid">
            {SOURCES.map((source) => (
              <label className="family-source-choice" key={source}>
                <input
                  checked={sources.includes(source)}
                  onChange={() => toggleSource(source)}
                  type="checkbox"
                />
                <span>{copy[source]}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <button className="button primary family-settings-save" disabled={busy} type="submit">
          {busy ? copy.saving : copy.save}
        </button>
      </form>
    </section>
  );
}
