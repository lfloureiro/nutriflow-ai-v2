import type { ReviewRecipe } from "./api/dietaryReviewClient";
import type { RecipeVariant, VariantOperation } from "./api/recipeVariantClient";

export function sameVariantOperations(
  left: Pick<VariantOperation, "recipe_ingredient_id" | "replacement_food_item_id" | "quantity" | "unit" | "preparation">[],
  right: Pick<VariantOperation, "recipe_ingredient_id" | "replacement_food_item_id" | "quantity" | "unit" | "preparation">[],
): boolean {
  if (left.length !== right.length) return false;
  const normalized = (row: typeof left[number]) =>
    [row.recipe_ingredient_id, row.replacement_food_item_id,
      Number(row.quantity.replace(",", ".")).toString(), row.unit.trim().toLowerCase(),
      row.preparation.trim().replace(/\s+/g," ").toLowerCase()].join("|");
  const a = left.map(normalized).sort();
  const b = right.map(normalized).sort();
  return a.every((value,index) => value === b[index]);
}

export function equivalentVariant(
  variants: RecipeVariant[],
  servings: string,
  operations: VariantOperation[],
): RecipeVariant | undefined {
  const count = Number(servings.replace(",", "."));
  if (!Number.isFinite(count) || count <= 0) return undefined;
  return variants.find(row => row.status !== "retired" &&
    Number(row.serving_count) === count &&
    sameVariantOperations(row.operations, operations));
}

export type RecipeProgress = {
  status: "needs_research" | "needs_product" | "needs_quantity" | "awaiting_review" | "active";
  blockedCount: number;
  issues: string[];
};

/** A suggestion is not clinical evidence or a complete recipe variant.
 * Only an active variant covering EVERY excluded ingredient can count active.
 */
export function recipeAdaptationProgress(
  recipe: ReviewRecipe,
  excludedIngredientIds: string[],
): RecipeProgress {
  const blocked = recipe.ingredients.filter(item => excludedIngredientIds.includes(item.id));
  const blockers: string[] = [];
  if (!blocked.length) return {status:"awaiting_review",blockedCount:0,issues:[]};
  const active = recipe.active_variants?.find(variant =>
    blocked.every(item => variant.operations.some(op => op.recipe_ingredient_id === item.id)));
  if (active) return {status:"active",blockedCount:blocked.length,issues:[]};
  let missingResearch = false;
  let missingProduct = false;
  let missingQuantity = false;
  for (const item of blocked) {
    const candidates = item.substitutions.filter(row => row.status !== "rejected");
    if (!candidates.length) {
      missingResearch = true;
      blockers.push(`${item.name}: sem alternativa registada`);
      continue;
    }
    const concrete = candidates.filter(row => !!row.replacement_food_item_id);
    if (!concrete.length) {
      missingProduct = true;
      blockers.push(`${item.name}: produto de catálogo por identificar`);
      continue;
    }
    if (!concrete.some(row => row.replacement_quantity &&
        Number(row.replacement_quantity.replace(",", ".")) > 0 && row.replacement_unit?.trim())) {
      missingQuantity = true;
      blockers.push(`${item.name}: quantidade da alternativa por confirmar`);
    }
  }
  const status = missingResearch ? "needs_research"
    : missingProduct ? "needs_product"
    : missingQuantity ? "needs_quantity" : "awaiting_review";
  return {status,blockedCount:blocked.length,issues:blockers};
}
