import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  ApiError,
  createFamilyRecipe,
  deactivateFamilyRecipe,
  listFamilyIngredients,
  listFamilyRecipes,
  updateFamilyRecipe,
} from "./api/client";
import type { Ingredient } from "./api/ingredientTypes";
import type {
  Recipe,
  RecipeCreate,
  RecipeIngredientWrite,
  RecipeMealType,
  RecipeNutritionEvidence,
} from "./api/recipeTypes";
import { useI18n, type Locale } from "./i18n";

const MEAL_TYPES: RecipeMealType[] = ["breakfast", "lunch", "snack", "dinner"];
type NutritionFilter = "all" | "ingredient_calculated" | "incomplete" | "synthetic_development";

const COPY = {
  "pt-PT": {
    eyebrow: "Casa · Receitas",
    title: "Receitas",
    help: "Receitas partilhadas do catálogo NutriFlow e receitas próprias da família.",
    search: "Procurar receitas",
    placeholder: "Ex.: bolonhesa, salmão…",
    showInactive: "Mostrar inativas",
    nutritionFilter: "Qualidade nutricional",
    filterAll: "Todas",
    filterCalculated: "Calculadas pelos ingredientes",
    filterIncomplete: "Incompletas",
    filterSynthetic: "Estimativas de desenvolvimento",
    newRecipe: "Nova receita",
    loading: "A carregar receitas…",
    empty: "Ainda não existem receitas.",
    emptySearch: "Nenhuma receita corresponde aos filtros.",
    edit: "Editar",
    view: "Ver",
    shared: "Partilhada",
    sharedTitle: "Receita partilhada",
    sharedHelp: "Esta receita pertence ao catálogo comum NutriFlow. Pode ser usada, avaliada e recomendada por qualquer família, mas não é alterada a partir desta família.",
    source: "Origem",
    inactive: "Inativa",
    back: "Voltar às receitas",
    createTitle: "Nova receita",
    editTitle: "Editar receita",
    identity: "Receita",
    name: "Nome",
    description: "Descrição / preparação",
    mealTypes: "Pode ser sugerida em",
    mealTypesHelp: "Isto impede, por exemplo, um pequeno-almoço de aparecer ao almoço ou jantar.",
    breakfast: "Pequeno-almoço",
    lunch: "Almoço",
    snack: "Lanche",
    dinner: "Jantar",
    servings: "Número de doses",
    yieldQuantity: "Rendimento final",
    yieldUnit: "Unidade do rendimento",
    ingredients: "Ingredientes",
    ingredientsHelp: "A ordem aqui é a ordem da receita. Cada ingrediente usa a composição nutricional mais recente disponível.",
    addIngredient: "Adicionar ingrediente",
    chooseIngredient: "Escolher ingrediente",
    quantity: "Quantidade",
    unit: "Unidade",
    preparation: "Preparação",
    up: "Subir",
    down: "Descer",
    remove: "Remover",
    save: "Guardar receita",
    saving: "A guardar…",
    deactivate: "Desativar receita",
    restore: "Reativar receita",
    confirmDeactivate: "Desativar esta receita? O histórico de refeições mantém-se intacto.",
    nutrition: "Nutrição",
    noNutrition: "Ainda sem cálculo nutricional utilizável.",
    nutritionIncomplete: "Nutrição incompleta",
    evidenceCalculated: "Calculada pelos ingredientes",
    evidenceSynthetic: "Estimativa de desenvolvimento",
    evidenceImported: "Nutrição importada",
    evidenceUnknown: "Origem nutricional desconhecida",
    syntheticHelp: "Este valor existe apenas para desenvolvimento/testes e não deve ser interpretado como nutrição real da receita. Será substituído quando os ingredientes tiverem dados nutricionais suficientes.",
    missingComposition: "Sem composição nutricional",
    missingEnergy: "Sem dados de energia",
    missingNutritionIngredients: "Ingredientes que bloqueiam o cálculo",
    nutritionBlockedHelp: "O total energético só é calculado quando todos os ingredientes têm composição, energia e unidades compatíveis.",
    total: "Receita total",
    perServing: "Por dose",
    issues: "Dados em falta",
    kcal: "kcal",
    requiredName: "Indica o nome da receita.",
    requiredMealType: "Seleciona pelo menos um tipo de refeição.",
    requiredIngredient: "Escolhe um ingrediente em todas as linhas.",
    invalidQuantity: "As quantidades têm de ser números maiores que zero.",
    invalidYield: "O rendimento e a respetiva unidade têm de ser preenchidos em conjunto.",
    error: "Não foi possível concluir a operação",
  },
  en: {
    eyebrow: "Home base · Recipes",
    title: "Recipes",
    help: "Shared NutriFlow catalogue recipes and the Family's own recipes.",
    search: "Search recipes",
    placeholder: "E.g. bolognese, salmon…",
    showInactive: "Show inactive",
    nutritionFilter: "Nutrition quality",
    filterAll: "All",
    filterCalculated: "Calculated from ingredients",
    filterIncomplete: "Incomplete",
    filterSynthetic: "Development estimates",
    newRecipe: "New recipe",
    loading: "Loading recipes…",
    empty: "There are no recipes yet.",
    emptySearch: "No recipes match the filters.",
    edit: "Edit",
    view: "View",
    shared: "Shared",
    sharedTitle: "Shared recipe",
    sharedHelp: "This recipe belongs to the shared NutriFlow catalogue. Any Family can use, rate and receive it as a recommendation, but this Family cannot modify it.",
    source: "Source",
    inactive: "Inactive",
    back: "Back to recipes",
    createTitle: "New recipe",
    editTitle: "Edit recipe",
    identity: "Recipe",
    name: "Name",
    description: "Description / preparation",
    mealTypes: "Can be suggested for",
    mealTypesHelp: "This prevents, for example, a breakfast recipe from appearing at lunch or dinner.",
    breakfast: "Breakfast",
    lunch: "Lunch",
    snack: "Snack",
    dinner: "Dinner",
    servings: "Serving count",
    yieldQuantity: "Finished yield",
    yieldUnit: "Yield unit",
    ingredients: "Ingredients",
    ingredientsHelp: "This order is the recipe order. Each ingredient uses the latest available nutrition composition.",
    addIngredient: "Add ingredient",
    chooseIngredient: "Choose ingredient",
    quantity: "Quantity",
    unit: "Unit",
    preparation: "Preparation",
    up: "Move up",
    down: "Move down",
    remove: "Remove",
    save: "Save recipe",
    saving: "Saving…",
    deactivate: "Deactivate recipe",
    restore: "Reactivate recipe",
    confirmDeactivate: "Deactivate this recipe? Meal history remains intact.",
    nutrition: "Nutrition",
    noNutrition: "No usable nutrition calculation yet.",
    nutritionIncomplete: "Incomplete nutrition",
    evidenceCalculated: "Calculated from ingredients",
    evidenceSynthetic: "Development estimate",
    evidenceImported: "Imported nutrition",
    evidenceUnknown: "Unknown nutrition origin",
    syntheticHelp: "This value exists only for development/testing and must not be interpreted as real recipe nutrition. It will be replaced when ingredient evidence is sufficient.",
    missingComposition: "No nutrition composition",
    missingEnergy: "No energy data",
    missingNutritionIngredients: "Ingredients blocking calculation",
    nutritionBlockedHelp: "Energy totals are only calculated when every ingredient has composition, energy and compatible units.",
    total: "Whole recipe",
    perServing: "Per serving",
    issues: "Missing evidence",
    kcal: "kcal",
    requiredName: "Enter a recipe name.",
    requiredMealType: "Select at least one meal type.",
    requiredIngredient: "Choose an ingredient on every row.",
    invalidQuantity: "Quantities must be numbers greater than zero.",
    invalidYield: "Yield quantity and unit must be provided together.",
    error: "The operation could not be completed",
  },
} as const;

type EditableIngredient = {
  foodItemId: string;
  quantity: string;
  unit: string;
  preparation: string;
};

type EditorValues = {
  name: string;
  description: string;
  mealTypes: RecipeMealType[];
  servingCount: string;
  yieldQuantity: string;
  yieldUnit: string;
  ingredients: EditableIngredient[];
};

export type RecipeNutritionBlocker = {
  ingredient: string;
  reason: "missing_composition" | "missing_energy";
};

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.message} (HTTP ${error.status})`;
  }
  return error instanceof Error ? error.message : String(error);
}

function decimalText(value: string): string {
  return value.trim().replace(",", ".");
}

function positive(value: string): boolean {
  const parsed = Number(decimalText(value));
  return Number.isFinite(parsed) && parsed > 0;
}

function initialValues(recipe: Recipe | null): EditorValues {
  return {
    name: recipe?.name ?? "",
    description: recipe?.description ?? "",
    mealTypes: recipe?.suitable_meal_types ?? ["lunch", "dinner"],
    servingCount: recipe?.serving_count ?? "4",
    yieldQuantity: recipe?.yield_quantity ?? "",
    yieldUnit: recipe?.yield_unit ?? "g",
    ingredients:
      recipe?.ingredients.map((ingredient) => ({
        foodItemId: ingredient.food_item_id,
        quantity: ingredient.quantity,
        unit: ingredient.unit,
        preparation: ingredient.preparation ?? "",
      })) ?? [],
  };
}

export function recipeNutritionBlockers(recipe: Recipe): RecipeNutritionBlocker[] {
  return recipe.ingredients.flatMap<RecipeNutritionBlocker>((ingredient) => {
    if (!ingredient.has_nutrition) {
      return [{ ingredient: ingredient.food_item_name, reason: "missing_composition" }];
    }
    if (!ingredient.has_energy) {
      return [{ ingredient: ingredient.food_item_name, reason: "missing_energy" }];
    }
    return [];
  });
}

export function recipeNutritionSummary(recipe: Recipe, locale: Locale): string {
  const composition = recipe.latest_composition;
  if (!composition || composition.energy_kcal === null) {
    return COPY[locale].noNutrition;
  }
  const formatter = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
  const total = formatter.format(Number(composition.energy_kcal));
  const perServing = composition.energy_per_serving_kcal;
  return perServing === null
    ? `${COPY[locale].total}: ${total} ${COPY[locale].kcal}`
    : `${COPY[locale].total}: ${total} ${COPY[locale].kcal} · ${COPY[locale].perServing}: ${formatter.format(Number(perServing))} ${COPY[locale].kcal}`;
}

function evidenceCopyKey(
  evidence: RecipeNutritionEvidence,
): "evidenceCalculated" | "evidenceSynthetic" | "evidenceImported" | "evidenceUnknown" {
  if (evidence === "ingredient_calculated") return "evidenceCalculated";
  if (evidence === "synthetic_development") return "evidenceSynthetic";
  if (evidence === "imported") return "evidenceImported";
  return "evidenceUnknown";
}

export function recipeNutritionEvidenceLabel(recipe: Recipe, locale: Locale): string {
  const evidence = recipe.latest_composition?.evidence ?? "unknown";
  return COPY[locale][evidenceCopyKey(evidence)];
}

function recipeNutritionState(recipe: Recipe): "ready" | "synthetic" | "missing" {
  const composition = recipe.latest_composition;
  if (!composition || composition.energy_kcal === null) return "missing";
  return composition.evidence === "synthetic_development" ? "synthetic" : "ready";
}

function issueCoveredByBlocker(issue: string): boolean {
  return (
    issue.includes(" has no nutrition composition.") ||
    issue === "At least one ingredient is missing energy data." ||
    issue.includes("Development-only synthetic nutrition estimate")
  );
}

function nutritionIssueText(issue: string, locale: Locale): string {
  if (locale !== "pt-PT") {
    return issue;
  }
  const conversion = /^Ingredient '(.+)' cannot be safely converted from '(.+)' to '(.+)'\.$/.exec(
    issue,
  );
  if (conversion) {
    return `${conversion[1]}: não é possível converter com segurança de ${conversion[2]} para ${conversion[3]}.`;
  }
  return issue;
}

function RecipeNutrition({ recipe }: { recipe: Recipe }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const blockers = recipeNutritionBlockers(recipe);
  const additionalIssues = recipe.nutrition_issues.filter((issue) => !issueCoveredByBlocker(issue));
  const state = recipeNutritionState(recipe);
  return (
    <section className="recipe-nutrition-panel">
      <div className="recipe-nutrition-heading">
        <h2>{copy.nutrition}</h2>
        <span className={`recipe-nutrition-state ${state}`}>
          {state === "missing" ? copy.nutritionIncomplete : recipeNutritionEvidenceLabel(recipe, locale)}
        </span>
      </div>
      <strong>{recipeNutritionSummary(recipe, locale)}</strong>
      {state === "synthetic" ? (
        <div className="recipe-evidence-note">
          <strong>{copy.evidenceSynthetic}</strong>
          <span>{copy.syntheticHelp}</span>
        </div>
      ) : null}
      {blockers.length > 0 || additionalIssues.length > 0 ? (
        <div className="recipe-issues">
          <span>{blockers.length > 0 ? copy.missingNutritionIngredients : copy.issues}</span>
          <ul>
            {blockers.map((blocker, index) => (
              <li key={`${blocker.ingredient}-${blocker.reason}-${index}`}>
                <strong>{blocker.ingredient}</strong> — {blocker.reason === "missing_composition" ? copy.missingComposition : copy.missingEnergy}
              </li>
            ))}
            {additionalIssues.map((issue) => (
              <li key={issue}>{nutritionIssueText(issue, locale)}</li>
            ))}
          </ul>
          {blockers.length > 0 ? <small>{copy.nutritionBlockedHelp}</small> : null}
        </div>
      ) : null}
    </section>
  );
}

function SharedRecipeViewer({ recipe, onDone }: { recipe: Recipe; onDone: () => void }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  return (
    <div className="recipe-editor">
      <button className="button ghost" onClick={onDone} type="button">
        ← {copy.back}
      </button>
      <header className="screen-header compact-screen-header">
        <div>
          <span className="eyebrow">{copy.sharedTitle}</span>
          <h1>{recipe.name}</h1>
          <p>{copy.sharedHelp}</p>
        </div>
      </header>

      <div className="recipe-form">
        <section className="recipe-form-card">
          <div className="recipe-section-heading">
            <div>
              <h2>{copy.identity}</h2>
              {recipe.description ? <p>{recipe.description}</p> : null}
            </div>
            <span className="ingredient-inactive">{copy.shared}</span>
          </div>
          <div className="person-detail-grid">
            <div className="person-detail-item">
              <span>{copy.mealTypes}</span>
              <strong>{recipe.suitable_meal_types.map((type) => copy[type]).join(" · ")}</strong>
            </div>
            <div className="person-detail-item">
              <span>{copy.servings}</span>
              <strong>{recipe.serving_count ?? "—"}</strong>
            </div>
            <div className="person-detail-item">
              <span>{copy.source}</span>
              <strong>{recipe.source}</strong>
            </div>
          </div>
        </section>

        <section className="recipe-form-card">
          <h2>{copy.ingredients}</h2>
          <div className="ingredient-list">
            {recipe.ingredients.map((ingredient) => (
              <div className="ingredient-row" key={ingredient.id}>
                <span className="ingredient-row__main">
                  <strong>{ingredient.food_item_name}</strong>
                  <small>
                    {ingredient.quantity} {ingredient.unit}
                    {ingredient.preparation ? ` · ${ingredient.preparation}` : ""}
                  </small>
                </span>
                <span className="ingredient-row__end">
                  <span
                    className={`recipe-nutrition-state ${ingredient.has_energy ? "ready" : "missing"}`}
                  >
                    {ingredient.has_energy
                      ? copy.evidenceCalculated
                      : ingredient.has_nutrition
                        ? copy.missingEnergy
                        : copy.missingComposition}
                  </span>
                </span>
              </div>
            ))}
          </div>
        </section>

        <RecipeNutrition recipe={recipe} />
      </div>
    </div>
  );
}

function RecipeEditor({
  familyId,
  recipe,
  ingredients,
  onDone,
}: {
  familyId: string;
  recipe: Recipe | null;
  ingredients: Ingredient[];
  onDone: () => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [values, setValues] = useState<EditorValues>(() => initialValues(recipe));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateIngredient(index: number, patch: Partial<EditableIngredient>) {
    setValues((current) => ({
      ...current,
      ingredients: current.ingredients.map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...patch } : item,
      ),
    }));
  }

  function moveIngredient(index: number, direction: -1 | 1) {
    setValues((current) => {
      const next = [...current.ingredients];
      const target = index + direction;
      if (target < 0 || target >= next.length) {
        return current;
      }
      [next[index], next[target]] = [next[target]!, next[index]!];
      return { ...current, ingredients: next };
    });
  }

  function toggleMealType(mealType: RecipeMealType) {
    setValues((current) => ({
      ...current,
      mealTypes: current.mealTypes.includes(mealType)
        ? current.mealTypes.filter((value) => value !== mealType)
        : [...current.mealTypes, mealType],
    }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!values.name.trim()) {
      setError(copy.requiredName);
      return;
    }
    if (values.mealTypes.length === 0) {
      setError(copy.requiredMealType);
      return;
    }
    if (values.ingredients.some((item) => !item.foodItemId)) {
      setError(copy.requiredIngredient);
      return;
    }
    if (values.ingredients.some((item) => !positive(item.quantity))) {
      setError(copy.invalidQuantity);
      return;
    }
    const hasYield = Boolean(values.yieldQuantity.trim());
    if (hasYield !== Boolean(values.yieldUnit.trim())) {
      setError(copy.invalidYield);
      return;
    }
    if (values.servingCount.trim() && !positive(values.servingCount)) {
      setError(copy.invalidQuantity);
      return;
    }

    const recipeIngredients: RecipeIngredientWrite[] = values.ingredients.map((item) => ({
      food_item_id: item.foodItemId,
      quantity: decimalText(item.quantity),
      unit: item.unit,
      preparation: item.preparation.trim() || null,
    }));
    const payload: RecipeCreate = {
      name: values.name.trim(),
      description: values.description.trim() || null,
      suitable_meal_types: values.mealTypes,
      serving_count: values.servingCount.trim() ? decimalText(values.servingCount) : null,
      yield_quantity: hasYield ? decimalText(values.yieldQuantity) : null,
      yield_unit: hasYield ? values.yieldUnit : null,
      ingredients: recipeIngredients,
    };

    setBusy(true);
    try {
      if (recipe === null) {
        await createFamilyRecipe(familyId, payload);
      } else {
        await updateFamilyRecipe(familyId, recipe.id, payload);
      }
      onDone();
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive() {
    if (recipe === null) {
      return;
    }
    if (recipe.is_active && !window.confirm(copy.confirmDeactivate)) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (recipe.is_active) {
        await deactivateFamilyRecipe(familyId, recipe.id);
      } else {
        await updateFamilyRecipe(familyId, recipe.id, { is_active: true });
      }
      onDone();
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="recipe-editor">
      <button className="button ghost" onClick={onDone} type="button">
        ← {copy.back}
      </button>
      <header className="screen-header compact-screen-header">
        <div>
          <span className="eyebrow">{copy.eyebrow}</span>
          <h1>{recipe ? copy.editTitle : copy.createTitle}</h1>
        </div>
      </header>
      {error ? (
        <div className="error-banner" role="alert">
          <strong>{copy.error}</strong>
          <span>{error}</span>
        </div>
      ) : null}
      <form className="recipe-form" onSubmit={submit}>
        <section className="recipe-form-card">
          <h2>{copy.identity}</h2>
          <div className="recipe-form-grid">
            <label className="field recipe-wide">
              <span>{copy.name}</span>
              <input
                autoFocus
                value={values.name}
                onChange={(event) => setValues({ ...values, name: event.target.value })}
              />
            </label>
            <label className="field recipe-wide">
              <span>{copy.description}</span>
              <textarea
                rows={4}
                value={values.description}
                onChange={(event) => setValues({ ...values, description: event.target.value })}
              />
            </label>
            <div className="field recipe-wide">
              <span>{copy.mealTypes}</span>
              <small className="muted">{copy.mealTypesHelp}</small>
              <div className="segmented-control">
                {MEAL_TYPES.map((mealType) => (
                  <button
                    className={values.mealTypes.includes(mealType) ? "active" : ""}
                    key={mealType}
                    onClick={() => toggleMealType(mealType)}
                    type="button"
                  >
                    {copy[mealType]}
                  </button>
                ))}
              </div>
            </div>
            <label className="field">
              <span>{copy.servings}</span>
              <input
                inputMode="decimal"
                value={values.servingCount}
                onChange={(event) => setValues({ ...values, servingCount: event.target.value })}
              />
            </label>
            <label className="field">
              <span>{copy.yieldQuantity}</span>
              <input
                inputMode="decimal"
                value={values.yieldQuantity}
                onChange={(event) => setValues({ ...values, yieldQuantity: event.target.value })}
              />
            </label>
            <label className="field">
              <span>{copy.yieldUnit}</span>
              <select
                value={values.yieldUnit}
                onChange={(event) => setValues({ ...values, yieldUnit: event.target.value })}
              >
                <option value="g">g</option>
                <option value="kg">kg</option>
                <option value="ml">ml</option>
                <option value="l">l</option>
              </select>
            </label>
          </div>
        </section>

        <section className="recipe-form-card">
          <div className="recipe-section-heading">
            <div>
              <h2>{copy.ingredients}</h2>
              <p>{copy.ingredientsHelp}</p>
            </div>
            <button
              className="button ghost"
              onClick={() =>
                setValues((current) => ({
                  ...current,
                  ingredients: [
                    ...current.ingredients,
                    { foodItemId: "", quantity: "100", unit: "g", preparation: "" },
                  ],
                }))
              }
              type="button"
            >
              + {copy.addIngredient}
            </button>
          </div>
          <div className="recipe-ingredient-list">
            {values.ingredients.map((item, index) => (
              <div className="recipe-ingredient-row" key={`${index}-${item.foodItemId}`}>
                <label className="field recipe-ingredient-name">
                  <span>{copy.ingredients}</span>
                  <select
                    value={item.foodItemId}
                    onChange={(event) => updateIngredient(index, { foodItemId: event.target.value })}
                  >
                    <option value="">{copy.chooseIngredient}</option>
                    {ingredients.map((ingredient) => (
                      <option key={ingredient.id} value={ingredient.id}>
                        {ingredient.name}
                        {ingredient.latest_composition === null
                          ? ` · ${copy.missingComposition}`
                          : ingredient.latest_composition.energy_kcal === null
                            ? ` · ${copy.missingEnergy}`
                            : ""}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>{copy.quantity}</span>
                  <input
                    inputMode="decimal"
                    value={item.quantity}
                    onChange={(event) => updateIngredient(index, { quantity: event.target.value })}
                  />
                </label>
                <label className="field">
                  <span>{copy.unit}</span>
                  <select
                    value={item.unit}
                    onChange={(event) => updateIngredient(index, { unit: event.target.value })}
                  >
                    <option value="g">g</option>
                    <option value="kg">kg</option>
                    <option value="ml">ml</option>
                    <option value="l">l</option>
                  </select>
                </label>
                <label className="field recipe-ingredient-prep">
                  <span>{copy.preparation}</span>
                  <input
                    value={item.preparation}
                    onChange={(event) => updateIngredient(index, { preparation: event.target.value })}
                  />
                </label>
                <div className="recipe-ingredient-actions">
                  <button disabled={index === 0} onClick={() => moveIngredient(index, -1)} type="button">
                    ↑ <span>{copy.up}</span>
                  </button>
                  <button
                    disabled={index === values.ingredients.length - 1}
                    onClick={() => moveIngredient(index, 1)}
                    type="button"
                  >
                    ↓ <span>{copy.down}</span>
                  </button>
                  <button
                    onClick={() =>
                      setValues((current) => ({
                        ...current,
                        ingredients: current.ingredients.filter((_, itemIndex) => itemIndex !== index),
                      }))
                    }
                    type="button"
                  >
                    × <span>{copy.remove}</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>

        {recipe ? <RecipeNutrition recipe={recipe} /> : null}

        <div className="recipe-form-actions">
          <button className="button primary" disabled={busy} type="submit">
            {busy ? copy.saving : copy.save}
          </button>
          {recipe ? (
            <button className="button ghost" disabled={busy} onClick={toggleActive} type="button">
              {recipe.is_active ? copy.deactivate : copy.restore}
            </button>
          ) : null}
        </div>
      </form>
    </div>
  );
}

function matchesNutritionFilter(recipe: Recipe, filter: NutritionFilter): boolean {
  if (filter === "all") return true;
  const composition = recipe.latest_composition;
  if (filter === "incomplete") return composition === null || composition.energy_kcal === null;
  if (filter === "synthetic_development") {
    return composition?.evidence === "synthetic_development";
  }
  return composition?.energy_kcal !== null && composition?.evidence === "ingredient_calculated";
}

export default function RecipeCatalogue({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [query, setQuery] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);
  const [nutritionFilter, setNutritionFilter] = useState<NutritionFilter>("all");
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [selected, setSelected] = useState<Recipe | null | undefined>(undefined);
  const [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (selected !== undefined) {
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      setBusy(true);
      setError(null);
      void Promise.all([
        listFamilyRecipes(familyId, query, includeInactive),
        listFamilyIngredients(familyId),
      ])
        .then(([recipeResult, ingredientResult]) => {
          if (!cancelled) {
            setRecipes(recipeResult);
            setIngredients(ingredientResult);
          }
        })
        .catch((caught: unknown) => {
          if (!cancelled) {
            setError(errorText(caught));
          }
        })
        .finally(() => {
          if (!cancelled) {
            setBusy(false);
          }
        });
    }, 160);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [familyId, includeInactive, query, revision, selected]);

  const hasSearch = useMemo(() => query.trim().length > 0 || nutritionFilter !== "all", [query, nutritionFilter]);
  const filteredRecipes = useMemo(
    () => recipes.filter((recipe) => matchesNutritionFilter(recipe, nutritionFilter)),
    [recipes, nutritionFilter],
  );

  if (selected !== undefined) {
    if (selected !== null && !selected.editable) {
      return <SharedRecipeViewer recipe={selected} onDone={() => setSelected(undefined)} />;
    }
    return (
      <RecipeEditor
        familyId={familyId}
        ingredients={ingredients}
        recipe={selected}
        onDone={() => {
          setSelected(undefined);
          setRevision((current) => current + 1);
        }}
      />
    );
  }

  return (
    <div className="recipe-catalogue">
      <header className="screen-header compact-screen-header recipe-header">
        <div>
          <span className="eyebrow">{copy.eyebrow}</span>
          <h1>{copy.title}</h1>
          <p>{copy.help}</p>
        </div>
        <button className="button primary" onClick={() => setSelected(null)} type="button">
          + {copy.newRecipe}
        </button>
      </header>
      <div className="recipe-toolbar">
        <label className="field recipe-search">
          <span>{copy.search}</span>
          <input
            placeholder={copy.placeholder}
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <label className="field recipe-quality-filter">
          <span>{copy.nutritionFilter}</span>
          <select
            value={nutritionFilter}
            onChange={(event) => setNutritionFilter(event.target.value as NutritionFilter)}
          >
            <option value="all">{copy.filterAll}</option>
            <option value="ingredient_calculated">{copy.filterCalculated}</option>
            <option value="incomplete">{copy.filterIncomplete}</option>
            <option value="synthetic_development">{copy.filterSynthetic}</option>
          </select>
        </label>
        <label className="ingredient-check">
          <input
            checked={includeInactive}
            onChange={(event) => setIncludeInactive(event.target.checked)}
            type="checkbox"
          />
          <span>{copy.showInactive}</span>
        </label>
      </div>
      {error ? (
        <div className="error-banner" role="alert">
          <strong>{copy.error}</strong>
          <span>{error}</span>
        </div>
      ) : null}
      {busy ? (
        <div className="shell-loading" role="status">{copy.loading}</div>
      ) : filteredRecipes.length === 0 ? (
        <div className="ingredient-empty">{hasSearch ? copy.emptySearch : copy.empty}</div>
      ) : (
        <div className="ingredient-list">
          {filteredRecipes.map((recipe) => {
            const state = recipeNutritionState(recipe);
            return (
              <button
                className="ingredient-row"
                key={recipe.id}
                onClick={() => setSelected(recipe)}
                type="button"
              >
                <span className="ingredient-row__main">
                  <strong>{recipe.name}</strong>
                  <small>
                    {recipe.suitable_meal_types.map((type) => copy[type]).join(" · ")} · {recipe.ingredients.length} {copy.ingredients.toLowerCase()} · {recipeNutritionSummary(recipe, locale)}
                  </small>
                </span>
                <span className="ingredient-row__end">
                  <span className={`recipe-nutrition-state ${state}`}>
                    {state === "missing" ? copy.nutritionIncomplete : recipeNutritionEvidenceLabel(recipe, locale)}
                  </span>
                  {recipe.scope === "shared" ? (
                    <span className="ingredient-inactive">{copy.shared}</span>
                  ) : null}
                  {!recipe.is_active ? <span className="ingredient-inactive">{copy.inactive}</span> : null}
                  <span>{recipe.editable ? copy.edit : copy.view} ›</span>
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
