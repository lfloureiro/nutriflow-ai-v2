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
import type { Recipe, RecipeCreate, RecipeIngredientWrite } from "./api/recipeTypes";
import { useI18n, type Locale } from "./i18n";

const COPY = {
  "pt-PT": {
    eyebrow: "Casa · Receitas",
    title: "Receitas",
    help: "Receitas reutilizáveis da família. Os valores nutricionais são calculados a partir dos ingredientes.",
    search: "Procurar receitas",
    placeholder: "Ex.: bolonhesa, salmão…",
    showInactive: "Mostrar inativas",
    newRecipe: "Nova receita",
    loading: "A carregar receitas…",
    empty: "Ainda não existem receitas.",
    emptySearch: "Nenhuma receita corresponde à pesquisa.",
    edit: "Editar",
    inactive: "Inativa",
    back: "Voltar às receitas",
    createTitle: "Nova receita",
    editTitle: "Editar receita",
    identity: "Receita",
    name: "Nome",
    description: "Descrição / preparação",
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
    nutrition: "Nutrição calculada",
    noNutrition: "Ainda sem cálculo nutricional utilizável.",
    total: "Receita total",
    perServing: "Por dose",
    issues: "Dados em falta",
    kcal: "kcal",
    requiredName: "Indica o nome da receita.",
    requiredIngredient: "Escolhe um ingrediente em todas as linhas.",
    invalidQuantity: "As quantidades têm de ser números maiores que zero.",
    invalidYield: "O rendimento e a respetiva unidade têm de ser preenchidos em conjunto.",
    error: "Não foi possível concluir a operação",
  },
  en: {
    eyebrow: "Home base · Recipes",
    title: "Recipes",
    help: "Reusable family recipes. Nutrition is calculated from ingredient composition evidence.",
    search: "Search recipes",
    placeholder: "E.g. bolognese, salmon…",
    showInactive: "Show inactive",
    newRecipe: "New recipe",
    loading: "Loading recipes…",
    empty: "There are no recipes yet.",
    emptySearch: "No recipes match the search.",
    edit: "Edit",
    inactive: "Inactive",
    back: "Back to recipes",
    createTitle: "New recipe",
    editTitle: "Edit recipe",
    identity: "Recipe",
    name: "Name",
    description: "Description / preparation",
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
    nutrition: "Calculated nutrition",
    noNutrition: "No usable nutrition calculation yet.",
    total: "Whole recipe",
    perServing: "Per serving",
    issues: "Missing evidence",
    kcal: "kcal",
    requiredName: "Enter a recipe name.",
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
  servingCount: string;
  yieldQuantity: string;
  yieldUnit: string;
  ingredients: EditableIngredient[];
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

function RecipeNutrition({ recipe }: { recipe: Recipe }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  return (
    <section className="recipe-nutrition-panel">
      <h2>{copy.nutrition}</h2>
      <strong>{recipeNutritionSummary(recipe, locale)}</strong>
      {recipe.nutrition_issues.length > 0 ? (
        <div className="recipe-issues">
          <span>{copy.issues}</span>
          <ul>
            {recipe.nutrition_issues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
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

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!values.name.trim()) {
      setError(copy.requiredName);
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

export default function RecipeCatalogue({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [query, setQuery] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);
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

  const hasSearch = useMemo(() => query.trim().length > 0, [query]);

  if (selected !== undefined) {
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
      ) : recipes.length === 0 ? (
        <div className="ingredient-empty">{hasSearch ? copy.emptySearch : copy.empty}</div>
      ) : (
        <div className="ingredient-list">
          {recipes.map((recipe) => (
            <button className="ingredient-row" key={recipe.id} onClick={() => setSelected(recipe)} type="button">
              <span className="ingredient-row__main">
                <strong>{recipe.name}</strong>
                <small>
                  {recipe.ingredients.length} {copy.ingredients.toLowerCase()} · {recipeNutritionSummary(recipe, locale)}
                </small>
              </span>
              <span className="ingredient-row__end">
                {!recipe.is_active ? <span className="ingredient-inactive">{copy.inactive}</span> : null}
                <span>{copy.edit} ›</span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
