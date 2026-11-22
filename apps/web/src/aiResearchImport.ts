import type { ReviewRecipe } from "./api/dietaryReviewClient";

export type AIResearchDraft = {
  recipe_id: string;
  ingredient_id: string;
  replacement_name: string;
  evidence_url: string;
  retailer_url?: string;
  notes: string;
  proposed_quantity?: string;
  proposed_unit?: string;
  evidence_status: "unverified";
};

export type AIResearchImport = {
  schema_version: "nutriflow.ai-review.v1";
  suggestions: AIResearchDraft[];
};

export type AIResearchPreviewRow = AIResearchDraft & {
  recipeName: string;
  ingredientName: string;
  issue?: string;
};

const safeHttps = (value: string) => {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password;
  } catch {
    return false;
  }
};

export function buildAIResearchExport(recipes: ReviewRecipe[], excluded: string[]): string {
  const relevant = new Set(excluded);
  return JSON.stringify({
    schema_version: "nutriflow.ai-review.v1",
    task: "Find evidence-based ingredient replacement candidates for the family's recipes. Return JSON matching schema_version, suggestions[]. Never claim clinical approval.",
    safety: "All substitutions are unverified, require label, portion and per-person review; do not mutate recipes, diets, meal plans or shopping lists.",
    ingredients: recipes.flatMap(recipe =>
      recipe.ingredients.filter(row => relevant.has(row.food_item_id)).map(row => ({
        recipe_id: recipe.id,
        recipe_name: recipe.name,
        ingredient_id: row.id,
        ingredient_name: row.name,
        original_quantity: row.quantity,
        original_unit: row.unit,
        existing_proposals: row.substitutions.filter(s => s.status !== "rejected").map(s => s.replacement_name),
      })),
    ),
    output_example: {
      schema_version: "nutriflow.ai-review.v1",
      suggestions: [{
        recipe_id: "copy a real recipe_id from ingredients",
        ingredient_id: "copy the corresponding ingredient_id",
        replacement_name: "specific proposed alternative",
        evidence_url: "https://official-source.example/reference",
        retailer_url: "https://shop.example/product",
        notes: "Evidence, published ingredients, date checked, uncertainty and portion to validate.",
        evidence_status: "unverified",
      }],
    },
  }, null, 2);
}

export function previewAIResearchImport(raw: string, recipes: ReviewRecipe[]): AIResearchPreviewRow[] {
  if (raw.length > 200_000) throw Error("Ficheiro JSON demasiado grande (máximo 200 KB).");
  let value: unknown;
  try { value = JSON.parse(raw); } catch { throw Error("JSON inválido."); }
  if (!value || typeof value !== "object" || Array.isArray(value)) throw Error("É necessário um objeto JSON.");
  const document = value as Record<string, unknown>;
  if (document.schema_version !== "nutriflow.ai-review.v1") throw Error("Versão do formato de importação não suportada.");
  if (!Array.isArray(document.suggestions) || document.suggestions.length > 200) throw Error("A lista suggestions é obrigatória (até 200).");
  const ingredientById = new Map(recipes.flatMap(recipe => recipe.ingredients.map(ingredient => [
    ingredient.id, {recipe, ingredient},
  ] as const)));
  const seen = new Set<string>();
  return document.suggestions.map((candidate, index) => {
    if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) throw Error(`Proposta ${index + 1} inválida.`);
    const row = candidate as Record<string, unknown>;
    const recipeId = row.recipe_id;
    const ingredientId = row.ingredient_id;
    const name = row.replacement_name;
    const notes = row.notes;
    const evidence = row.evidence_url;
    if (typeof recipeId !== "string" || typeof ingredientId !== "string" || typeof name !== "string" ||
        typeof notes !== "string" || typeof evidence !== "string" || row.evidence_status !== "unverified" ||
        name.trim().length < 2 || name.length > 160 || notes.length > 5000 ||
        !safeHttps(evidence) ||
        (row.retailer_url !== undefined && (typeof row.retailer_url !== "string" || !safeHttps(row.retailer_url)))) {
      throw Error(`Proposta ${index + 1}: campos, evidência HTTPS ou estado inválidos.`);
    }
    const original = ingredientById.get(ingredientId);
    if (!original || original.recipe.id !== recipeId) throw Error(`Proposta ${index + 1}: receita ou ingrediente não pertence à família.`);
    const quantity = row.proposed_quantity;
    const unit = row.proposed_unit;
    if ((quantity !== undefined || unit !== undefined) &&
        (typeof quantity !== "string" || typeof unit !== "string" ||
         !/^\d+(?:[.,]\d+)?$/.test(quantity) || Number(quantity.replace(",", ".")) <= 0 ||
         unit.trim().length === 0 || unit.length > 24)) {
      throw Error(`Proposta ${index + 1}: quantidade e unidade precisam de revisão conjunta.`);
    }
    const duplicateKey = `${ingredientId}:${name.trim().toLocaleLowerCase()}`;
    const existing = original.ingredient.substitutions.some(s =>
      s.status !== "rejected" && s.replacement_name.trim().toLocaleLowerCase() === name.trim().toLocaleLowerCase());
    const repeated = seen.has(duplicateKey);
    seen.add(duplicateKey);
    return {
      recipe_id: recipeId,
      ingredient_id: ingredientId,
      replacement_name: name.trim(),
      evidence_url: evidence,
      ...(typeof row.retailer_url === "string" ? {retailer_url: row.retailer_url} : {}),
      notes,
      ...(typeof quantity === "string" && typeof unit === "string"
        ? {proposed_quantity: quantity, proposed_unit: unit} : {}),
      evidence_status: "unverified" as const,
      recipeName: original.recipe.name,
      ingredientName: original.ingredient.name,
      ...(existing || repeated ? {issue: "Proposta já registada ou repetida no ficheiro."} : {}),
    };
  });
}
