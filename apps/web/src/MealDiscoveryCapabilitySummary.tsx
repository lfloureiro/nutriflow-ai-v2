import { useEffect, useState } from "react";

import { getMealDiscoveryCapabilities } from "./api/setupClient";
import type {
  MealDiscoveryCapability,
  MealDiscoverySource,
} from "./api/setupTypes";
import { useI18n } from "./i18n";

const SOURCE_LABELS: Record<MealDiscoverySource, Record<"pt-PT" | "en", string>> = {
  shared_recipes: { "pt-PT": "Receitas", en: "Recipes" },
  uber_eats: { "pt-PT": "Uber Eats", en: "Uber Eats" },
  glovo: { "pt-PT": "Glovo", en: "Glovo" },
  bolt_food: { "pt-PT": "Bolt Food", en: "Bolt Food" },
  restaurants: { "pt-PT": "Restaurantes", en: "Restaurants" },
};

const STATUS_LABELS = {
  "pt-PT": {
    ready: "Disponível",
    needs_configuration: "Falta configurar",
    integration_required: "Integração necessária",
    disabled: "Desativado",
  },
  en: {
    ready: "Available",
    needs_configuration: "Needs configuration",
    integration_required: "Integration required",
    disabled: "Disabled",
  },
} as const;

function detail(capability: MealDiscoveryCapability, locale: "pt-PT" | "en"): string {
  if (locale === "en") return capability.detail;
  if (capability.source === "shared_recipes") {
    return "Catálogo partilhado e receitas próprias da família prontos a usar.";
  }
  if (capability.source === "restaurants") {
    if (capability.status === "ready") {
      return "Descoberta live de restaurantes através de OpenStreetMap disponível.";
    }
    if (capability.status === "needs_configuration") {
      return "Define uma área de restaurantes para ativar a pesquisa live.";
    }
    return "Pesquisa live de restaurantes desativada nesta instalação.";
  }

  const provider = SOURCE_LABELS[capability.source][locale];
  if (capability.live) return `${provider} está operacional para pesquisa live.`;
  if (capability.credentials_configured === false) {
    return `Faltam as credenciais de ${provider} no secret store desta instalação.`;
  }
  if (capability.access_enabled === false) {
    return `As credenciais de ${provider} existem, mas o acesso consumer ainda não está aprovado/ativado.`;
  }
  if (capability.adapter_available === false) {
    return `Credenciais e acesso de ${provider} estão configurados; falta registar o adapter executável.`;
  }
  return `A integração consumer de ${provider} ainda não está operacional.`;
}

export default function MealDiscoveryCapabilitySummary({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const [capabilities, setCapabilities] = useState<MealDiscoveryCapability[]>([]);

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

  if (capabilities.length === 0) return null;

  return (
    <div className="meal-capability-grid">
      {capabilities.map((capability) => (
        <article className="meal-capability-card" key={capability.source}>
          <div>
            <strong>{SOURCE_LABELS[capability.source][locale]}</strong>
            <span className={`meal-capability-status status-${capability.status}`}>
              {STATUS_LABELS[locale][capability.status]}
            </span>
          </div>
          <small>{detail(capability, locale)}</small>
        </article>
      ))}
    </div>
  );
}
