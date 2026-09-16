import type { Locale } from "./i18n";
import type { MealPlanFitGuideline, MealPlanFitRule, PlanFitConflict } from "./api/planFitTypes";

const TARGET_LABELS: Record<string, { "pt-PT": string; en: string }> = {
  energy: { "pt-PT": "Energia", en: "Energy" },
  energy_kcal: { "pt-PT": "Energia", en: "Energy" },
  calories: { "pt-PT": "Energia", en: "Energy" },
  protein: { "pt-PT": "Proteína", en: "Protein" },
  fiber: { "pt-PT": "Fibra", en: "Fiber" },
  sodium: { "pt-PT": "Sódio", en: "Sodium" },
  saturated_fat: { "pt-PT": "Gordura saturada", en: "Saturated fat" },
};

const SOURCE_LABELS: Record<string, { "pt-PT": string; en: string }> = {
  demo: { "pt-PT": "Demo", en: "Demo" },
  "NutriFlow development demo": {
    "pt-PT": "Demo de desenvolvimento NutriFlow",
    en: "NutriFlow development demo",
  },
};

function normalizedOperator(rule: MealPlanFitRule): "min" | "max" | "range" | "target" | "exclude" | "other" {
  if (["min", "gte", ">=", ">"].includes(rule.operator)) return "min";
  if (["max", "lte", "<=", "<"].includes(rule.operator)) return "max";
  if (rule.operator === "range") return "range";
  if (rule.operator === "target") return "target";
  if (rule.operator === "exclude") return "exclude";
  return "other";
}

export function planFitTargetLabel(key: string, locale: Locale): string {
  const known = TARGET_LABELS[key];
  if (known) return known[locale];
  const fallback = key.replaceAll("_", " ");
  return fallback.charAt(0).toUpperCase() + fallback.slice(1);
}

export function planFitSourceLabel(value: string | null | undefined, locale: Locale): string {
  if (!value) return "NutriFlow";
  return SOURCE_LABELS[value]?.[locale] ?? value;
}

export function formatPlanFitNumber(value: string | null | undefined, locale: Locale): string {
  if (value === null || value === undefined || value === "") return "—";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return value;
  return new Intl.NumberFormat(locale === "pt-PT" ? "pt-PT" : "en", {
    maximumFractionDigits: 2,
  }).format(numeric);
}

export function planFitUnitLabel(
  unit: string | null | undefined,
  locale: Locale,
  quantity?: string | number | null,
): string {
  if (!unit) return "";
  if (unit === "serving" || unit === "servings") {
    const numeric = quantity === null || quantity === undefined ? 1 : Number(quantity);
    const plural = Number.isFinite(numeric) && Math.abs(numeric) !== 1;
    if (locale === "pt-PT") return plural ? "porções" : "porção";
    return plural ? "servings" : "serving";
  }
  return unit;
}

export function planFitRuleExplanation(rule: MealPlanFitRule, locale: Locale): string {
  const operator = normalizedOperator(rule);
  const daily = rule.scope === "daily";

  if (rule.status === "support") {
    if (locale === "pt-PT") {
      return operator === "range"
        ? "Esta porção aproxima o total diário do intervalo-alvo."
        : "Esta porção aproxima o total diário do mínimo, mas ainda não o atinge.";
    }
    return operator === "range"
      ? "This portion moves the daily total toward the target range."
      : "This portion moves the daily total toward the minimum but does not reach it yet.";
  }

  if (rule.status === "unknown" || rule.status === "not_evaluated") {
    return locale === "pt-PT"
      ? "Não há dados suficientes para avaliar esta regra com segurança."
      : "There is not enough evidence to evaluate this rule safely.";
  }

  if (operator === "exclude") {
    if (locale === "pt-PT") {
      return rule.status === "pass"
        ? "A receita não contém o alimento ou item excluído."
        : "A receita contém um alimento ou item excluído.";
    }
    return rule.status === "pass"
      ? "The recipe does not contain the excluded food or item."
      : "The recipe contains an excluded food or item.";
  }

  if (daily) {
    if (locale === "pt-PT") {
      return rule.status === "pass"
        ? "O total diário projetado cumpre esta regra."
        : "O total diário projetado não cumpre esta regra.";
    }
    return rule.status === "pass"
      ? "The projected daily total meets this rule."
      : "The projected daily total does not meet this rule.";
  }

  if (locale === "pt-PT") {
    if (operator === "min") return rule.status === "pass" ? "A porção cumpre o mínimo." : "A porção fica abaixo do mínimo.";
    if (operator === "max") return rule.status === "pass" ? "A porção mantém-se dentro do máximo." : "A porção excede o máximo.";
    if (operator === "range") return rule.status === "pass" ? "A porção está dentro do intervalo-alvo." : "A porção está fora do intervalo-alvo.";
    if (operator === "target") return rule.status === "pass" ? "A porção corresponde ao valor-alvo." : "A porção difere do valor-alvo.";
    return rule.status === "pass" ? "A porção cumpre esta regra." : "A porção não cumpre esta regra.";
  }

  if (operator === "min") return rule.status === "pass" ? "The portion meets the minimum." : "The portion is below the minimum.";
  if (operator === "max") return rule.status === "pass" ? "The portion stays within the maximum." : "The portion exceeds the maximum.";
  if (operator === "range") return rule.status === "pass" ? "The portion is inside the target range." : "The portion is outside the target range.";
  if (operator === "target") return rule.status === "pass" ? "The portion matches the target value." : "The portion differs from the target value.";
  return rule.status === "pass" ? "The portion meets this rule." : "The portion does not meet this rule.";
}

export function planFitGuidelineExplanation(
  _guideline: MealPlanFitGuideline,
  locale: Locale,
): string {
  return locale === "pt-PT"
    ? "Esta orientação é apresentada para contexto, mas ainda não entra na pontuação automática."
    : "This guidance is shown for context but is not yet included in automatic scoring.";
}

export function planFitConflictMessage(conflict: PlanFitConflict, locale: Locale): string {
  const target = planFitTargetLabel(conflict.target_key, locale);
  return locale === "pt-PT"
    ? `Existem regras ${conflict.severity === "mandatory" ? "obrigatórias" : "de recomendação"} incompatíveis para ${target}.`
    : `There are incompatible ${conflict.severity === "mandatory" ? "mandatory" : "advisory"} rules for ${target}.`;
}

export function planFitSafetyIssue(issue: string, locale: Locale): string {
  if (issue.startsWith("mandatory_reaction:")) {
    return locale === "pt-PT"
      ? "A receita ativa um bloqueio obrigatório associado a uma reação alimentar."
      : "The recipe triggers a mandatory food-reaction safety block.";
  }
  return locale === "pt-PT" ? "Existe um bloqueio de segurança obrigatório." : "There is a mandatory safety block.";
}
