import {useUnsavedChanges} from "./useUnsavedChanges";
import {requestNavigation} from "./navigation";
import {browseRecipes,defaultRecipeBrowse,readRecipeBrowse,storeRecipeBrowse,searchText,isAdaptedRecipe,recipeHasImage,type RecipeBrowse} from "./recipeBrowsing";
import RecipeTastePanel from "./ui/RecipeTastePanel";
import Icon from "./ui/Icon";
import {resolveMealHeroImage} from "./mealHeroImages";
import ContextDrawer from "./ui/ContextDrawer";
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

function RecipeCardArt({name,imageUrl}: {name:string;imageUrl?:string|null}) {
  const resolved = resolveMealHeroImage({planned:{title:name},recipeImageUrl:imageUrl});
  const [failedSrc,setFailedSrc] = useState<string[]>([]);
  const image = resolved && !failedSrc.includes(resolved.src)
    ? {...resolved,src:resolved.src}
    : resolved?.fallbackSrc && !failedSrc.includes(resolved.fallbackSrc)
      ? {...resolved,src:resolved.fallbackSrc}
      : null;
  return <span className="nf-recipe-art" aria-label={image?.alt ?? name}>
    {image ?
      <img src={image.src} alt="" loading="lazy" referrerPolicy="no-referrer"
        title={resolved?.kind==="generated"?"Imagem ilustrativa gerada por IA":undefined}
        onError={() => setFailedSrc(previous=>[...previous,image.src])} /> :
      <Icon name="book" />}
  </span>;
}

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
    deactivate: "Apagar receita",
    restore: "Reativar receita",
    confirmDeactivate: "Apagar esta receita da lista ativa? O histórico de refeições mantém-se intacto e podes recuperá-la em Mostrar inativas.",
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
    deactivate: "Delete recipe",
    restore: "Reactivate recipe",
    confirmDeactivate: "Remove this recipe from active recipes? Meal history remains intact and it can be restored via Show inactive.",
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
  rowId:string;
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
    servingCount: recipe?.serving_count ?? "",
    yieldQuantity: recipe?.yield_quantity ?? "",
    yieldUnit: recipe?.yield_unit ?? "",
    ingredients:
      recipe?.ingredients.map((ingredient) => ({
        rowId:crypto.randomUUID(),
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
  seedRecipe,
  ingredients,
  onDone,
}: {
  familyId: string;
  recipe: Recipe | null;
  seedRecipe?:Recipe;
  ingredients: Ingredient[];
  onDone: () => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [values, setValues] = useState<EditorValues>(() => {const values=initialValues(recipe??seedRecipe??null);return seedRecipe?{...values,name:`${values.name} · ${locale==="pt-PT"?"cópia":"copy"}`.slice(0,100)}:values;});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [ingredientQuery,setIngredientQuery]=useState("");
  const guard=useUnsavedChanges(values,locale==="pt-PT"?"Tens alterações na receita por guardar. Sair e descartá-las?":"You have unsaved recipe changes. Leave and discard them?");
  const closeEditor=()=>{if(!busy&&guard.confirmDiscard())onDone();};
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
      guard.markSaved();onDone();
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
    if(!guard.confirmDiscard())return;
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
      guard.markSaved();onDone();
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="recipe-editor">
      {seedRecipe&&<p className="decision-result">{locale==="pt-PT"?"Cópia editável de ":"Editable copy of "}<strong>{seedRecipe.name}</strong> · {locale==="pt-PT"?"a original mantém-se intacta":"the original stays unchanged"}</p>}
      {guard.dirty&&<p className="nf-draft-state" role="status">{locale==="pt-PT"?"Alterações por guardar":"Unsaved changes"}</p>}
      <button className="button ghost" onClick={closeEditor} type="button">
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
      <form className="recipe-form" onSubmit={submit}><fieldset className="nf-form-lock" disabled={busy}>
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
                <option value="">{locale==="pt-PT"?"Sem rendimento indicado":"No yield specified"}</option>
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
                    { rowId:crypto.randomUUID(),foodItemId: "", quantity: "100", unit: "g", preparation: "" },
                  ],
                }))
              }
              type="button"
            >
              + {copy.addIngredient}
            </button>
          </div>
          <label className="field"><span>{locale==="pt-PT"?"Pesquisar ingredientes disponíveis":"Search available ingredients"}</span><input type="search" value={ingredientQuery} onChange={event=>setIngredientQuery(event.target.value)} placeholder={locale==="pt-PT"?"Ex.: arroz, batata…":"E.g. rice, potato…"}/></label>
          <div className="recipe-ingredient-list">
            {values.ingredients.map((item, index) => (
              <div className="recipe-ingredient-row" key={item.rowId}>
                <label className="field recipe-ingredient-name">
                  <span>{copy.ingredients}</span>
                  <select
                    value={item.foodItemId}
                    onChange={(event) => updateIngredient(index, { foodItemId: event.target.value })}
                  >
                    <option value="">{copy.chooseIngredient}</option>
                    {ingredients.filter(ingredient=>ingredient.id===item.foodItemId||searchText(ingredient.name).includes(searchText(ingredientQuery))).map((ingredient) => (
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
                    {item.unit&&!["g","kg","ml","l"].includes(item.unit)&&<option value={item.unit}>{item.unit}</option>}
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
      </fieldset></form>
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
  const savedBrowse=useMemo(()=>readRecipeBrowse(familyId),[familyId]);
  const [query, setQuery] = useState(savedBrowse.query);
  const [includeInactive, setIncludeInactive] = useState(savedBrowse.includeInactive);
  const [nutritionFilter, setNutritionFilter] = useState<NutritionFilter>(savedBrowse.nutrition);
  const [mealFilter,setMealFilter]=useState<RecipeBrowse["meal"]>(savedBrowse.meal);
  const [originFilter,setOriginFilter]=useState<RecipeBrowse["origin"]>(savedBrowse.origin);
  const [imageFilter,setImageFilter]=useState<RecipeBrowse["image"]>(savedBrowse.image);
  const [sortOrder,setSortOrder]=useState<RecipeBrowse["sort"]>(savedBrowse.sort);
  const [seedRecipe,setSeedRecipe]=useState<Recipe|undefined>();
  useEffect(()=>{storeRecipeBrowse(familyId,{query,includeInactive,nutrition:nutritionFilter,meal:mealFilter,origin:originFilter,image:imageFilter,sort:sortOrder});},[familyId,query,includeInactive,nutritionFilter,mealFilter,originFilter,imageFilter,sortOrder]);
  function clearFilters(){setQuery("");setIncludeInactive(false);setNutritionFilter("all");setMealFilter("all");setOriginFilter("all");setImageFilter("all");setSortOrder(defaultRecipeBrowse.sort);}
  function copyRecipe(recipe:Recipe){if(!requestNavigation())return;setSeedRecipe(recipe);setSelected(null);}
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [selected, setSelected] = useState<Recipe | null | undefined>(undefined);
  const [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
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
  }, [familyId, includeInactive, query, revision]);

  const hasSearch = useMemo(() => query.trim().length > 0 || nutritionFilter !== "all"||mealFilter!=="all"||originFilter!=="all"||imageFilter!=="all"||includeInactive, [query, nutritionFilter,mealFilter,originFilter,imageFilter,includeInactive]);
  const filteredRecipes = useMemo(
    () => browseRecipes(recipes.filter(recipe=>matchesNutritionFilter(recipe,nutritionFilter)),{query,includeInactive,nutrition:nutritionFilter,meal:mealFilter,origin:originFilter,image:imageFilter,sort:sortOrder},locale),
    [recipes,nutritionFilter,mealFilter,originFilter,imageFilter,sortOrder,locale],
  );

  const missingImageCount = recipes.filter(recipe=>!recipeHasImage(recipe)).length;

  const editorPanel = selected !== undefined ? (
    <ContextDrawer
      title={selected?.name ?? copy.newRecipe}
      wide
      closeLabel={locale === "pt-PT" ? "Fechar detalhe" : "Close detail"}
      onRequestClose={() => {
        if (!requestNavigation()) return false;
        setSeedRecipe(undefined);
        setSelected(undefined);
        return true;
      }}
    >
      {selected !== null && !selected.editable ? (
        <>
          <button type="button" className="button secondary" onClick={()=>copyRecipe(selected)}>{locale==="pt-PT"?"Criar cópia para a família":"Create family copy"}</button>
          <SharedRecipeViewer recipe={selected} onDone={() => setSelected(undefined)} />
          {selected.scope === "family" && selected.is_active && (
            <button type="button" className="button ghost"
              onClick={async () => {
                if (!window.confirm(copy.confirmDeactivate)) return;
                try {
                  await deactivateFamilyRecipe(familyId, selected.id);
                  setSelected(undefined);
                  setRevision(current => current + 1);
                } catch (caught: unknown) {
                  setError(errorText(caught));
                }
              }}>
              {copy.deactivate}
            </button>
          )}
          <RecipeTastePanel key={selected.id} familyId={familyId} recipe={selected}/>
        </>
      ) : (
        <>
          {selected&&<button type="button" className="button secondary" onClick={()=>copyRecipe(selected)}>{locale==="pt-PT"?"Criar cópia para a família":"Create family copy"}</button>}
          <RecipeEditor key={selected?.id??seedRecipe?.id??"new"}
            seedRecipe={selected===null?seedRecipe:undefined}
            familyId={familyId}
            ingredients={ingredients}
            recipe={selected}
            onDone={() => {
              setSeedRecipe(undefined);setSelected(undefined);
              setRevision((current) => current + 1);
            }}
          />
          {selected ? <RecipeTastePanel key={selected.id} familyId={familyId} recipe={selected}/> : null}
        </>
      )}
    </ContextDrawer>
  ) : null;

  return (
    <div className="recipe-catalogue">
      <header className="screen-header compact-screen-header recipe-header">
        <div>
          <span className="eyebrow">{copy.eyebrow}</span>
          <h1>{copy.title}</h1>
          <p>{copy.help}</p>
        </div>
        <button className="button primary" disabled={busy} onClick={() => {setSeedRecipe(undefined);setSelected(null);}} type="button">
          + {copy.newRecipe}
        </button>
      </header>
      {filteredRecipes.length > 0 && !busy ? (() => {
        // Only feature an actual recipe from the current, permission-filtered
        // catalogue. This is a visual highlight, not a medical recommendation.
        const photoRecipe = filteredRecipes.find(recipe =>
          resolveMealHeroImage({planned:{title:recipe.name}}) !== null);
        const featured = photoRecipe ?? filteredRecipes[0]!;
        return <div className="nf-recipe-editorial-row">
          <button type="button" className="nf-recipe-feature" onClick={() => setSelected(featured)}>
            <RecipeCardArt name={featured.name} imageUrl={featured.image_url}/>
            <span className="nf-recipe-feature-copy">
              <small>{locale === "pt-PT" ? "RECEITA DO CATÁLOGO" : "FROM THE CATALOGUE"}</small>
              <strong>{featured.name}</strong>
              <span>{featured.suitable_meal_types.map(type => copy[type]).join(" · ")} · {featured.ingredients.length} {copy.ingredients.toLowerCase()}</span>
              <em>{locale === "pt-PT" ? "Ver receita" : "View recipe"} ›</em>
            </span>
          </button>
          <aside className="nf-recipe-feature-aside">
            <strong>{locale === "pt-PT" ? "Explorar adaptações" : "Explore adaptations"}</strong>
            <p>{locale === "pt-PT" ?
              "Revê ingredientes, dados nutricionais e possíveis alterações antes de confirmar." :
              "Review ingredients, nutrition data and possible changes before confirming."}</p>
            <button type="button" className="button ghost small" onClick={() => setSelected(featured)}>
              {locale === "pt-PT" ? "Abrir detalhe" : "Open details"}
            </button>
          </aside>
        </div>;
      })() : null}
      <div className="recipe-toolbar nf-recipe-browse-toolbar">
        <label className="field recipe-search">
          <span>{copy.search}</span>
          <input
            placeholder={copy.placeholder}
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      </div>
      <details className="nf-recipe-filter-tools"><summary>{locale==="pt-PT"?"Filtros e ordenação":"Filters and sorting"}{(nutritionFilter!=="all"||mealFilter!=="all"||originFilter!=="all"||imageFilter!=="all"||includeInactive)&&<span> · {locale==="pt-PT"?"ativos":"active"}</span>}</summary><div className="nf-filter-options">
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
      <div className="nf-catalogue-context"><label className="field"><span>{locale==="pt-PT"?"Imagem da receita":"Recipe image"}</span><select value={imageFilter} onChange={e=>setImageFilter(e.target.value as RecipeBrowse["image"])}><option value="all">{copy.filterAll}</option><option value="with">{locale==="pt-PT"?"Com imagem":"With image"}</option><option value="without">{locale==="pt-PT"?"Sem imagem":"Missing image"}</option></select></label><label className="field"><span>{locale==="pt-PT"?"Tempo de refeição":"Meal type"}</span><select value={mealFilter} onChange={e=>setMealFilter(e.target.value as RecipeBrowse["meal"])}><option value="all">{copy.filterAll}</option>{MEAL_TYPES.map(type=><option key={type} value={type}>{copy[type]}</option>)}</select></label><label className="field"><span>{locale==="pt-PT"?"Origem da receita":"Recipe origin"}</span><select value={originFilter} onChange={e=>setOriginFilter(e.target.value as RecipeBrowse["origin"])}><option value="all">{copy.filterAll}</option><option value="shared">{copy.shared}</option><option value="family">{locale==="pt-PT"?"Próprias da família":"Family originals"}</option><option value="adapted">{locale==="pt-PT"?"Adaptações":"Adaptations"}</option></select></label><label className="field"><span>{locale==="pt-PT"?"Ordenar por":"Sort by"}</span><select value={sortOrder} onChange={e=>setSortOrder(e.target.value as RecipeBrowse["sort"])}><option value="name">{locale==="pt-PT"?"Nome A–Z":"Name A–Z"}</option><option value="updated">{locale==="pt-PT"?"Atualizadas recentemente":"Recently updated"}</option><option value="ingredients">{locale==="pt-PT"?"Menos ingredientes":"Fewer ingredients"}</option></select></label></div>
      </div></details>
      <div className="nf-catalogue-results"><p role="status">{busy?copy.loading:`${filteredRecipes.length} ${locale==="pt-PT"?"receitas encontradas":"recipes found"}`}</p>{!busy&&missingImageCount>0&&<button className="button ghost small" type="button" aria-pressed={imageFilter==="without"} onClick={()=>setImageFilter(current=>current==="without"?"all":"without")}>{locale==="pt-PT"?`Sem imagem (${missingImageCount})`:`Missing images (${missingImageCount})`}</button>}{hasSearch&&<button className="button ghost small" type="button" onClick={clearFilters}>{locale==="pt-PT"?"Limpar filtros":"Clear filters"}</button>}</div>
      {error ? (
        <div className="error-banner" role="alert">
          <strong>{copy.error}</strong>
          <span>{error}</span>
        </div>
      ) : null}
      {busy && recipes.length === 0 ? (
        <div className="shell-loading" role="status">{copy.loading}</div>
      ) : filteredRecipes.length === 0 && !busy ? (
        <div className="ingredient-empty">{hasSearch ? copy.emptySearch : copy.empty}</div>
      ) : (
        <div className="nf-recipe-grid">
          {filteredRecipes.map((recipe) => {
            const state = recipeNutritionState(recipe);
            return (
              <button
                className="nf-recipe-card"
                key={recipe.id}
                onClick={() => setSelected(recipe)}
                type="button"
              >
                <RecipeCardArt name={recipe.name} imageUrl={recipe.image_url}/>
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
                  {isAdaptedRecipe(recipe)&&<span className="ingredient-inactive">{locale==="pt-PT"?"Adaptação":"Adaptation"}</span>}
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
      {editorPanel}
    </div>
  );
}
