import { useI18n } from "./i18n";
import {
  budgetProgress,
  type RecommendationNutritionBudget,
} from "./recommendationNutrition";

const COPY = {
  "pt-PT": {
    title: "Orçamento calórico do dia",
    target: "Meta",
    consumed: "Consumidas",
    planned: "Planeadas",
    assumed: "Assumidas",
    assumedHelp: "Estimativa usada quando o pequeno-almoço ainda não foi declarado.",
    remaining: "Restam",
    unavailable: "Sem objetivo definido",
  },
  en: {
    title: "Daily calorie budget",
    target: "Target",
    consumed: "Consumed",
    planned: "Planned",
    assumed: "Assumed",
    assumedHelp: "Estimate used when breakfast has not been declared yet.",
    remaining: "Remaining",
    unavailable: "No target defined",
  },
} as const;

function kcal(value: number, locale: string): string {
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(value)} kcal`;
}

function range(
  minimum: number | null,
  maximum: number | null,
  locale: string,
  fallback: string,
): string {
  if (minimum === null && maximum === null) return fallback;
  if (minimum !== null && maximum !== null) {
    if (Math.round(minimum) === Math.round(maximum)) return kcal(minimum, locale);
    return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(minimum)}–${kcal(maximum, locale)}`;
  }
  return kcal(minimum ?? maximum ?? 0, locale);
}

export default function RecommendationNutritionBudgetPanel({
  budgets,
}: {
  budgets: RecommendationNutritionBudget[];
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  if (budgets.length === 0) return null;

  return (
    <div className="nutrition-budget-panel">
      <span className="nutrition-budget-panel__title">{copy.title}</span>
      <div className="nutrition-budget-grid">
        {budgets.map((budget) => {
          const progress = budgetProgress(budget);
          return (
            <article className="nutrition-budget-card" key={budget.personId}>
              <div className="nutrition-budget-card__heading">
                <strong>{budget.personName}</strong>
                <span>
                  {copy.target}: {range(budget.targetMinKcal, budget.targetMaxKcal, locale, copy.unavailable)}
                </span>
              </div>
              {progress !== null ? (
                <div className="nutrition-budget-progress" aria-hidden="true">
                  <span style={{ width: `${Math.round(progress * 100)}%` }} />
                </div>
              ) : null}
              <div className="nutrition-budget-stats">
                <span><small>{copy.consumed}</small><strong>{kcal(budget.consumedKcal, locale)}</strong></span>
                <span><small>{copy.planned}</small><strong>{kcal(budget.plannedKcal, locale)}</strong></span>
                <span title={copy.assumedHelp}><small>{copy.assumed}</small><strong>{kcal(budget.assumedKcal, locale)}</strong></span>
                <span><small>{copy.remaining}</small><strong>{range(budget.remainingMinKcal, budget.remainingMaxKcal, locale, "—")}</strong></span>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
