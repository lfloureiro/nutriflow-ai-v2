import { useEffect, useState } from "react";

import { ApiError, listFamilyPersons } from "./api/client";
import {
  getPersonMealDiscovery,
  updatePersonMealDiscovery,
} from "./api/setupClient";
import type {
  MealDiscoverySource,
  PersonMealDiscovery,
} from "./api/setupTypes";
import type { Person } from "./api/types";
import { useI18n } from "./i18n";

const SOURCES: MealDiscoverySource[] = [
  "shared_recipes",
  "uber_eats",
  "glovo",
  "bolt_food",
  "restaurants",
];

const COPY = {
  "pt-PT": {
    title: "Preferências por pessoa",
    help: "Por defeito todos herdam as fontes da família. Personaliza apenas quando alguém usa providers, morada ou área diferentes.",
    inherit: "Herdar da família",
    custom: "Personalizar",
    shared_recipes: "Receitas",
    uber_eats: "Uber Eats",
    glovo: "Glovo",
    bolt_food: "Bolt Food",
    restaurants: "Restaurantes",
    deliveryAddress: "Morada de entrega",
    restaurantArea: "Área de restaurantes",
    save: "Guardar",
    saving: "A guardar…",
    loading: "A carregar pessoas…",
    sourceRequired: "Seleciona pelo menos uma fonte.",
    deliveryRequired: "Indica uma morada para as entregas.",
    areaRequired: "Indica uma área para restaurantes.",
    error: "Não foi possível atualizar as fontes desta pessoa",
  },
  en: {
    title: "Preferences by person",
    help: "Everyone inherits Family sources by default. Customize only when someone uses different providers, address or area.",
    inherit: "Inherit from Family",
    custom: "Customize",
    shared_recipes: "Recipes",
    uber_eats: "Uber Eats",
    glovo: "Glovo",
    bolt_food: "Bolt Food",
    restaurants: "Restaurants",
    deliveryAddress: "Delivery address",
    restaurantArea: "Restaurant area",
    save: "Save",
    saving: "Saving…",
    loading: "Loading people…",
    sourceRequired: "Select at least one source.",
    deliveryRequired: "Enter a delivery address.",
    areaRequired: "Enter a restaurant area.",
    error: "Could not update this person's sources",
  },
} as const;

type Draft = {
  inherit: boolean;
  sources: MealDiscoverySource[];
  deliveryAddress: string;
  restaurantArea: string;
};

function errorText(error: unknown): string {
  if (error instanceof ApiError) return `${error.message} (HTTP ${error.status})`;
  return error instanceof Error ? error.message : String(error);
}

function displayName(person: Person): string {
  return [person.first_name, person.last_name].filter(Boolean).join(" ");
}

function toDraft(discovery: PersonMealDiscovery): Draft {
  return {
    inherit: discovery.inherits_family_defaults,
    sources: [...discovery.meal_discovery_sources],
    deliveryAddress: discovery.delivery_address ?? "",
    restaurantArea: discovery.restaurant_area ?? "",
  };
}

function usesDelivery(sources: MealDiscoverySource[]): boolean {
  return sources.some(
    (source) => source === "uber_eats" || source === "glovo" || source === "bolt_food",
  );
}

export default function PersonMealDiscoveryOverrides({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [people, setPeople] = useState<Person[]>([]);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [errorById, setErrorById] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void listFamilyPersons(familyId)
      .then(async (loaded) => {
        const discoveries = await Promise.all(
          loaded.map((person) => getPersonMealDiscovery(person.id)),
        );
        if (cancelled) return;
        setPeople(loaded);
        setDrafts(
          Object.fromEntries(
            loaded.map((person, index) => [person.id, toDraft(discoveries[index]!)]),
          ),
        );
      })
      .catch((caught: unknown) => {
        if (!cancelled) setErrorById({ general: errorText(caught) });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [familyId]);

  function patch(personId: string, next: Partial<Draft>) {
    setDrafts((current) => ({
      ...current,
      [personId]: { ...current[personId]!, ...next },
    }));
  }

  function toggleSource(personId: string, source: MealDiscoverySource) {
    const draft = drafts[personId];
    if (!draft) return;
    patch(personId, {
      sources: draft.sources.includes(source)
        ? draft.sources.filter((value) => value !== source)
        : [...draft.sources, source],
    });
  }

  async function save(person: Person) {
    const draft = drafts[person.id];
    if (!draft) return;
    if (!draft.inherit && draft.sources.length === 0) {
      setErrorById((current) => ({ ...current, [person.id]: copy.sourceRequired }));
      return;
    }
    if (!draft.inherit && usesDelivery(draft.sources) && !draft.deliveryAddress.trim()) {
      setErrorById((current) => ({ ...current, [person.id]: copy.deliveryRequired }));
      return;
    }
    if (!draft.inherit && draft.sources.includes("restaurants") && !draft.restaurantArea.trim()) {
      setErrorById((current) => ({ ...current, [person.id]: copy.areaRequired }));
      return;
    }

    setBusyId(person.id);
    setErrorById((current) => ({ ...current, [person.id]: "" }));
    try {
      const updated = await updatePersonMealDiscovery(person.id, {
        inherit_family_defaults: draft.inherit,
        meal_discovery_sources: draft.inherit ? null : draft.sources,
        delivery_address: draft.inherit ? null : draft.deliveryAddress.trim() || null,
        restaurant_area: draft.inherit ? null : draft.restaurantArea.trim() || null,
      });
      setDrafts((current) => ({ ...current, [person.id]: toDraft(updated) }));
    } catch (caught: unknown) {
      setErrorById((current) => ({ ...current, [person.id]: errorText(caught) }));
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <div className="shell-loading">{copy.loading}</div>;

  return (
    <section className="person-source-overrides">
      <header>
        <h2>{copy.title}</h2>
        <p>{copy.help}</p>
      </header>
      {errorById.general ? (
        <div className="error-banner"><strong>{copy.error}</strong><span>{errorById.general}</span></div>
      ) : null}
      <div className="person-source-override-list">
        {people.map((person) => {
          const draft = drafts[person.id];
          if (!draft) return null;
          return (
            <article className="person-source-override-card" key={person.id}>
              <div className="person-source-override-heading">
                <strong>{displayName(person)}</strong>
                <label className="ingredient-check">
                  <input
                    checked={draft.inherit}
                    onChange={(event) => patch(person.id, { inherit: event.target.checked })}
                    type="checkbox"
                  />
                  <span>{draft.inherit ? copy.inherit : copy.custom}</span>
                </label>
              </div>
              {!draft.inherit ? (
                <>
                  <div className="person-source-pills">
                    {SOURCES.map((source) => (
                      <label className={`meal-source-setting ${draft.sources.includes(source) ? "selected" : ""}`} key={source}>
                        <input
                          checked={draft.sources.includes(source)}
                          onChange={() => toggleSource(person.id, source)}
                          type="checkbox"
                        />
                        <strong>{copy[source]}</strong>
                      </label>
                    ))}
                  </div>
                  {usesDelivery(draft.sources) ? (
                    <label className="field">
                      <span>{copy.deliveryAddress}</span>
                      <input
                        value={draft.deliveryAddress}
                        onChange={(event) => patch(person.id, { deliveryAddress: event.target.value })}
                      />
                    </label>
                  ) : null}
                  {draft.sources.includes("restaurants") ? (
                    <label className="field">
                      <span>{copy.restaurantArea}</span>
                      <input
                        value={draft.restaurantArea}
                        onChange={(event) => patch(person.id, { restaurantArea: event.target.value })}
                      />
                    </label>
                  ) : null}
                </>
              ) : null}
              {errorById[person.id] ? (
                <div className="error-banner"><strong>{copy.error}</strong><span>{errorById[person.id]}</span></div>
              ) : null}
              <button
                className="button ghost"
                disabled={busyId === person.id}
                onClick={() => void save(person)}
                type="button"
              >
                {busyId === person.id ? copy.saving : copy.save}
              </button>
            </article>
          );
        })}
      </div>
    </section>
  );
}
