import type { Recipe, RecipeNutritionEvidence } from "./api/recipeTypes";
import { useI18n, type Locale } from "./i18n";
import "./recipe-evidence.css";

const COPY = {
  "pt-PT": {
    title: "Qualidade dos dados da receita",
    ingredient_calculated: "Calculada a partir dos ingredientes",
    imported: "Composição importada",
    synthetic_development: "Dados de desenvolvimento",
    unknown: "Composição incompleta",
    ingredients: "Ingredientes com dados nutricionais",
    energyCoverage: "Ingredientes com energia",
    nutrients: "Nutrientes estruturados",
    onlyEnergy:
      "Para esta receita existe energia, mas ainda não existem macronutrientes suficientes para uma comparação nutricional completa.",
    noNutrition:
      "A receita ainda não tem composição nutricional estruturada suficiente para uma comparação completa.",
    partialIngredients:
      "Há ingredientes sem composição nutricional suficiente; os valores apresentados devem ser tratados como cobertura parcial.",
    complete:
      "A composição disponível permite avaliar os nutrientes estruturados apresentados abaixo.",
    showIngredients: "Ver ingredientes e cobertura",
    withNutrition: "com dados",
    withoutNutrition: "sem dados",
  },
  en: {
    title: "Recipe data quality",
    ingredient_calculated: "Calculated from ingredients",
    imported: "Imported composition",
    synthetic_development: "Development data",
    unknown: "Incomplete composition",
    ingredients: "Ingredients with nutrition data",
    energyCoverage: "Ingredients with energy",
    nutrients: "Structured nutrients",
    onlyEnergy:
      "Energy is available for this recipe, but there are not enough macronutrient data for a complete nutrition comparison.",
    noNutrition:
      "The recipe does not yet have enough structured nutrition data for a complete comparison.",
    partialIngredients:
      "Some ingredients lack sufficient nutrition composition; displayed values should be treated as partial coverage.",
    complete:
      "The available composition supports evaluation of the structured nutrients shown below.",
    showIngredients: "Show ingredients and coverage",
    withNutrition: "with data",
    withoutNutrition: "without data",
  },
} as const;

export type RecipeEvidenceSummary = {
  evidence: RecipeNutritionEvidence;
  ingredientCount: number;
  nutritionIngredientCount: number;
  energyIngredientCount: number;
  nutrientCount: number;
  hasEnergy: boolean;
  hasIssues: boolean;
};

export function recipeEvidenceSummary(recipe: Recipe): RecipeEvidenceSummary {
  return {
    evidence: recipe.latest_composition?.evidence ?? "unknown",
    ingredientCount: recipe.ingredients.length,
    nutritionIngredientCount: recipe.ingredients.filter(
      (ingredient) => ingredient.has_nutrition,
    ).length,
    energyIngredientCount: recipe.ingredients.filter(
      (ingredient) => ingredient.has_energy,
    ).length,
    nutrientCount: recipe.latest_composition?.nutrients.length ?? 0,
    hasEnergy: recipe.latest_composition?.energy_kcal !== null &&
      recipe.latest_composition?.energy_kcal !== undefined,
    hasIssues: recipe.nutrition_issues.length > 0,
  };
}

export function recipeEvidenceMessage(
  summary: RecipeEvidenceSummary,
  locale: Locale,
): string {
  const copy = COPY[locale];
  if (!summary.hasEnergy && summary.nutrientCount === 0) return copy.noNutrition;
  if (summary.nutrientCount === 0) return copy.onlyEnergy;
  if (
    summary.hasIssues ||
    summary.nutritionIngredientCount < summary.ingredientCount ||
    summary.energyIngredientCount < summary.ingredientCount
  ) {
    return copy.partialIngredients;
  }
  return copy.complete;
}

export default function RecipeEvidencePanel({ recipe }: { recipe: Recipe }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const summary = recipeEvidenceSummary(recipe);

  return (
    <section className="recipe-evidence">
      <div className="recipe-evidence__heading">
        <strong>{copy.title}</strong>
        <span>{copy[summary.evidence]}</span>
      </div>
      <p>{recipeEvidenceMessage(summary, locale)}</p>
      <div className="recipe-evidence__stats">
        <span>
          <small>{copy.ingredients}</small>
          <strong>
            {summary.nutritionIngredientCount}/{summary.ingredientCount}
          </strong>
        </span>
        <span>
          <small>{copy.energyCoverage}</small>
          <strong>
            {summary.energyIngredientCount}/{summary.ingredientCount}
          </strong>
        </span>
        <span>
          <small>{copy.nutrients}</small>
          <strong>{summary.nutrientCount}</strong>
        </span>
      </div>
      {recipe.ingredients.length > 0 ? (
        <details>
          <summary>{copy.showIngredients}</summary>
          <ul className="recipe-evidence__ingredients">
            {recipe.ingredients.map((ingredient) => (
              <li key={ingredient.id}>
                <span>
                  <strong>{ingredient.food_item_name}</strong>
                  <small>
                    {ingredient.quantity} {ingredient.unit}
                  </small>
                </span>
                <em>
                  {ingredient.has_nutrition
                    ? copy.withNutrition
                    : copy.withoutNutrition}
                </em>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}
