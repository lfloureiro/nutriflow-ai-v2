import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  ApiError,
  createFamilyIngredient,
  deactivateFamilyIngredient,
  listFamilyIngredients,
  updateFamilyIngredient,
} from "./api/client";
import type {
  Ingredient,
  IngredientCompositionWrite,
  IngredientNutrientWrite,
} from "./api/ingredientTypes";
import { useI18n, type Locale } from "./i18n";

const COPY = {
  "pt-PT": {
    eyebrow: "Casa · Ingredientes",
    title: "Ingredientes",
    help: "Consulta os ingredientes partilhados do catálogo NutriFlow e mantém os ingredientes próprios da família. A nutrição fica versionada para alimentar receitas e planeamento.",
    search: "Procurar ingredientes",
    searchPlaceholder: "Ex.: aveia, tomate, salmão…",
    showInactive: "Mostrar inativos",
    newIngredient: "Novo ingrediente",
    loading: "A carregar ingredientes…",
    empty: "Ainda não existem ingredientes neste catálogo.",
    emptySearch: "Nenhum ingrediente corresponde à pesquisa.",
    noComposition: "Sem composição nutricional",
    inactive: "Inativo",
    shared: "Partilhado",
    readOnly: "Só leitura",
    edit: "Editar",
    back: "Voltar aos ingredientes",
    createTitle: "Novo ingrediente",
    editTitle: "Editar ingrediente",
    details: "Identificação",
    nutrition: "Composição nutricional",
    nutritionHelp: "Valores para a quantidade de referência. Ao alterar nutrição é criada uma nova versão; o histórico anterior não é reescrito.",
    name: "Nome",
    brand: "Marca / origem",
    description: "Descrição",
    referenceQuantity: "Quantidade de referência",
    referenceUnit: "Unidade",
    energy: "Energia (kcal)",
    protein: "Proteína (g)",
    carbohydrate: "Hidratos (g)",
    fat: "Gordura (g)",
    fiber: "Fibra (g)",
    sodium: "Sódio (mg)",
    save: "Guardar",
    saving: "A guardar…",
    deactivate: "Desativar ingrediente",
    restore: "Reativar ingrediente",
    confirmDeactivate: "Desativar este ingrediente? As receitas e o histórico continuam intactos.",
    requiredName: "Indica o nome do ingrediente.",
    invalidNutrition: "A quantidade de referência tem de ser superior a zero; os restantes valores nutricionais têm de ser iguais ou superiores a zero.",
    error: "Não foi possível concluir a operação",
    kcal: "kcal",
  },
  en: {
    eyebrow: "Home base · Ingredients",
    title: "Ingredients",
    help: "Browse shared NutriFlow catalogue ingredients and maintain the Family's own ingredients. Nutrition remains versioned so recipes and planning can use traceable evidence.",
    search: "Search ingredients",
    searchPlaceholder: "E.g. oats, tomato, salmon…",
    showInactive: "Show inactive",
    newIngredient: "New ingredient",
    loading: "Loading ingredients…",
    empty: "There are no ingredients in this catalogue yet.",
    emptySearch: "No ingredients match this search.",
    noComposition: "No nutrition composition",
    inactive: "Inactive",
    shared: "Shared",
    readOnly: "Read only",
    edit: "Edit",
    back: "Back to ingredients",
    createTitle: "New ingredient",
    editTitle: "Edit ingredient",
    details: "Identity",
    nutrition: "Nutrition composition",
    nutritionHelp: "Values are for the reference quantity. Nutrition edits create a new version instead of rewriting history.",
    name: "Name",
    brand: "Brand / source",
    description: "Description",
    referenceQuantity: "Reference quantity",
    referenceUnit: "Unit",
    energy: "Energy (kcal)",
    protein: "Protein (g)",
    carbohydrate: "Carbohydrate (g)",
    fat: "Fat (g)",
    fiber: "Fibre (g)",
    sodium: "Sodium (mg)",
    save: "Save",
    saving: "Saving…",
    deactivate: "Deactivate ingredient",
    restore: "Reactivate ingredient",
    confirmDeactivate: "Deactivate this ingredient? Recipes and history will remain intact.",
    requiredName: "Enter an ingredient name.",
    invalidNutrition: "Reference quantity must be greater than zero; all other nutrition values must be greater than or equal to zero.",
    error: "The operation could not be completed",
    kcal: "kcal",
  },
} as const;

type NutrientKey = "protein" | "carbohydrate" | "fat" | "fiber" | "sodium";

type EditorValues = {
  name: string;
  brand: string;
  description: string;
  referenceQuantity: string;
  referenceUnit: string;
  energy: string;
  protein: string;
  carbohydrate: string;
  fat: string;
  fiber: string;
  sodium: string;
};

const NUTRIENT_UNITS: Record<NutrientKey, string> = {
  protein: "g",
  carbohydrate: "g",
  fat: "g",
  fiber: "g",
  sodium: "mg",
};

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.message} (HTTP ${error.status})`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

function nutrientValue(ingredient: Ingredient | null, key: NutrientKey): string {
  const nutrient = ingredient?.latest_composition?.nutrients.find((item) => item.key === key);
  return nutrient?.value ?? "";
}

function editorValues(ingredient: Ingredient | null): EditorValues {
  const composition = ingredient?.latest_composition;
  return {
    name: ingredient?.name ?? "",
    brand: ingredient?.brand ?? "",
    description: ingredient?.description ?? "",
    referenceQuantity: composition?.reference_quantity ?? "100",
    referenceUnit: composition?.reference_unit ?? "g",
    energy: composition?.energy_kcal ?? "",
    protein: nutrientValue(ingredient, "protein"),
    carbohydrate: nutrientValue(ingredient, "carbohydrate"),
    fat: nutrientValue(ingredient, "fat"),
    fiber: nutrientValue(ingredient, "fiber"),
    sodium: nutrientValue(ingredient, "sodium"),
  };
}

function validNonNegativeNumber(value: string): boolean {
  if (!value.trim()) {
    return true;
  }
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) && parsed >= 0;
}

function validPositiveNumber(value: string): boolean {
  const normalized = value.trim() || "100";
  const parsed = Number(normalized.replace(",", "."));
  return Number.isFinite(parsed) && parsed > 0;
}

function decimalText(value: string): string {
  return value.trim().replace(",", ".");
}

export function buildIngredientComposition(
  values: EditorValues,
): IngredientCompositionWrite | null {
  const nutritionKeys: NutrientKey[] = ["protein", "carbohydrate", "fat", "fiber", "sodium"];
  const hasNutrition = Boolean(values.energy.trim()) || nutritionKeys.some((key) => values[key].trim());
  if (!hasNutrition) {
    return null;
  }

  const nutrients: IngredientNutrientWrite[] = nutritionKeys
    .filter((key) => values[key].trim())
    .map((key) => ({
      key,
      value: decimalText(values[key]),
      unit: NUTRIENT_UNITS[key],
    }));

  return {
    reference_quantity: decimalText(values.referenceQuantity || "100"),
    reference_unit: values.referenceUnit.trim() || "g",
    energy_kcal: values.energy.trim() ? decimalText(values.energy) : null,
    nutrients,
  };
}

export function ingredientNutritionSummary(ingredient: Ingredient, locale: Locale): string {
  const composition = ingredient.latest_composition;
  if (!composition) {
    return COPY[locale].noComposition;
  }
  const reference = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(
    Number(composition.reference_quantity),
  );
  if (composition.energy_kcal === null) {
    return `${reference} ${composition.reference_unit}`;
  }
  const energy = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(
    Number(composition.energy_kcal),
  );
  return `${reference} ${composition.reference_unit} · ${energy} ${COPY[locale].kcal}`;
}

function IngredientEditor({
  familyId,
  ingredient,
  onBack,
  onSaved,
}: {
  familyId: string;
  ingredient: Ingredient | null;
  onBack: () => void;
  onSaved: () => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [values, setValues] = useState<EditorValues>(() => editorValues(ingredient));
  const [nutritionDirty, setNutritionDirty] = useState(ingredient === null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update(field: keyof EditorValues, value: string, nutrition = false) {
    setValues((current) => ({ ...current, [field]: value }));
    if (nutrition) {
      setNutritionDirty(true);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!values.name.trim()) {
      setError(copy.requiredName);
      return;
    }

    const nonNegativeFields = [
      values.energy,
      values.protein,
      values.carbohydrate,
      values.fat,
      values.fiber,
      values.sodium,
    ];
    if (
      nutritionDirty &&
      (!validPositiveNumber(values.referenceQuantity) ||
        nonNegativeFields.some((value) => !validNonNegativeNumber(value)))
    ) {
      setError(copy.invalidNutrition);
      return;
    }

    const composition = nutritionDirty ? buildIngredientComposition(values) : undefined;
    setBusy(true);
    try {
      if (ingredient === null) {
        await createFamilyIngredient(familyId, {
          name: values.name.trim(),
          brand: values.brand.trim() || null,
          description: values.description.trim() || null,
          composition,
        });
      } else {
        await updateFamilyIngredient(familyId, ingredient.id, {
          name: values.name.trim(),
          brand: values.brand.trim() || null,
          description: values.description.trim() || null,
          ...(nutritionDirty ? { composition } : {}),
        });
      }
      onSaved();
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive() {
    if (ingredient === null) {
      return;
    }
    if (ingredient.is_active && !window.confirm(copy.confirmDeactivate)) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (ingredient.is_active) {
        await deactivateFamilyIngredient(familyId, ingredient.id);
      } else {
        await updateFamilyIngredient(familyId, ingredient.id, { is_active: true });
      }
      onSaved();
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ingredient-editor">
      <button className="button ghost ingredient-back" onClick={onBack} type="button">
        ← {copy.back}
      </button>
      <header className="screen-header compact-screen-header">
        <div>
          <span className="eyebrow">{copy.eyebrow}</span>
          <h1>{ingredient ? copy.editTitle : copy.createTitle}</h1>
        </div>
      </header>

      {error ? (
        <div className="error-banner" role="alert">
          <strong>{copy.error}</strong>
          <span>{error}</span>
        </div>
      ) : null}

      <form className="ingredient-form" onSubmit={submit}>
        <section className="ingredient-form-card">
          <h2>{copy.details}</h2>
          <div className="ingredient-form-grid">
            <label className="field ingredient-field-wide">
              <span>{copy.name}</span>
              <input
                autoFocus
                maxLength={160}
                value={values.name}
                onChange={(event) => update("name", event.target.value)}
              />
            </label>
            <label className="field">
              <span>{copy.brand}</span>
              <input
                maxLength={120}
                value={values.brand}
                onChange={(event) => update("brand", event.target.value)}
              />
            </label>
            <label className="field ingredient-field-wide">
              <span>{copy.description}</span>
              <textarea
                rows={3}
                value={values.description}
                onChange={(event) => update("description", event.target.value)}
              />
            </label>
          </div>
        </section>

        <section className="ingredient-form-card">
          <div className="ingredient-section-heading">
            <div>
              <h2>{copy.nutrition}</h2>
              <p>{copy.nutritionHelp}</p>
            </div>
          </div>
          <div className="ingredient-nutrition-grid">
            <label className="field">
              <span>{copy.referenceQuantity}</span>
              <input
                inputMode="decimal"
                value={values.referenceQuantity}
                onChange={(event) => update("referenceQuantity", event.target.value, true)}
              />
            </label>
            <label className="field">
              <span>{copy.referenceUnit}</span>
              <select
                value={values.referenceUnit}
                onChange={(event) => update("referenceUnit", event.target.value, true)}
              >
                <option value="g">g</option>
                <option value="kg">kg</option>
                <option value="ml">ml</option>
                <option value="l">l</option>
              </select>
            </label>
            <label className="field">
              <span>{copy.energy}</span>
              <input
                inputMode="decimal"
                value={values.energy}
                onChange={(event) => update("energy", event.target.value, true)}
              />
            </label>
            {(["protein", "carbohydrate", "fat", "fiber", "sodium"] as NutrientKey[]).map(
              (key) => (
                <label className="field" key={key}>
                  <span>{copy[key]}</span>
                  <input
                    inputMode="decimal"
                    value={values[key]}
                    onChange={(event) => update(key, event.target.value, true)}
                  />
                </label>
              ),
            )}
          </div>
        </section>

        <div className="ingredient-form-actions">
          <button className="button primary" disabled={busy} type="submit">
            {busy ? copy.saving : copy.save}
          </button>
          {ingredient ? (
            <button className="button ghost" disabled={busy} onClick={toggleActive} type="button">
              {ingredient.is_active ? copy.deactivate : copy.restore}
            </button>
          ) : null}
        </div>
      </form>
    </div>
  );
}

function IngredientRow({
  ingredient,
  locale,
  onEdit,
}: {
  ingredient: Ingredient;
  locale: Locale;
  onEdit: () => void;
}) {
  const copy = COPY[locale];
  const content = (
    <>
      <span className="ingredient-row__main">
        <strong>{ingredient.name}</strong>
        <small>
          {ingredient.brand ? `${ingredient.brand} · ` : ""}
          {ingredientNutritionSummary(ingredient, locale)}
          {ingredient.scope === "shared" ? ` · ${ingredient.source}` : ""}
        </small>
      </span>
      <span className="ingredient-row__end">
        {!ingredient.is_active ? <span className="ingredient-inactive">{copy.inactive}</span> : null}
        {ingredient.scope === "shared" ? (
          <>
            <span className="ingredient-inactive">{copy.shared}</span>
            <span>{copy.readOnly}</span>
          </>
        ) : (
          <span>{copy.edit} ›</span>
        )}
      </span>
    </>
  );

  if (!ingredient.editable) {
    return <div className="ingredient-row ingredient-row--readonly">{content}</div>;
  }
  return (
    <button className="ingredient-row" onClick={onEdit} type="button">
      {content}
    </button>
  );
}

export default function IngredientCatalogue({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [query, setQuery] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Ingredient | null | undefined>(undefined);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    if (selected !== undefined) {
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      setBusy(true);
      setError(null);
      void listFamilyIngredients(familyId, query, includeInactive)
        .then((result) => {
          if (!cancelled) {
            setIngredients(result);
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
    }, 180);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [familyId, query, includeInactive, revision, selected]);

  const hasSearch = useMemo(() => query.trim().length > 0, [query]);

  if (selected !== undefined) {
    return (
      <IngredientEditor
        familyId={familyId}
        ingredient={selected}
        onBack={() => setSelected(undefined)}
        onSaved={() => {
          setSelected(undefined);
          setRevision((current) => current + 1);
        }}
      />
    );
  }

  return (
    <div className="ingredient-catalogue">
      <header className="screen-header compact-screen-header ingredient-header">
        <div>
          <span className="eyebrow">{copy.eyebrow}</span>
          <h1>{copy.title}</h1>
          <p>{copy.help}</p>
        </div>
        <button className="button primary" onClick={() => setSelected(null)} type="button">
          + {copy.newIngredient}
        </button>
      </header>

      <div className="ingredient-toolbar">
        <label className="field ingredient-search">
          <span>{copy.search}</span>
          <input
            placeholder={copy.searchPlaceholder}
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
        <div className="shell-loading" role="status">
          {copy.loading}
        </div>
      ) : ingredients.length === 0 ? (
        <div className="ingredient-empty">{hasSearch ? copy.emptySearch : copy.empty}</div>
      ) : (
        <div className="ingredient-list">
          {ingredients.map((ingredient) => (
            <IngredientRow
              ingredient={ingredient}
              key={ingredient.id}
              locale={locale}
              onEdit={() => setSelected(ingredient)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
