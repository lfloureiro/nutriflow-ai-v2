export type RecipeMealType = "breakfast" | "lunch" | "snack" | "dinner";

export type RecipeIngredient = {
  id: string;
  food_item_id: string;
  food_item_name: string;
  quantity: string;
  unit: string;
  preparation: string | null;
  notes: string | null;
  sort_order: number;
  has_nutrition: boolean;
};

export type RecipeNutrient = {
  key: string;
  total_value: string;
  unit: string;
  per_serving_value: string | null;
};

export type RecipeComposition = {
  id: string;
  reference_quantity: string;
  reference_unit: string;
  energy_kcal: string | null;
  energy_per_serving_kcal: string | null;
  composition_version: string;
  calculation_version: string;
  computed_at: string;
  nutrients: RecipeNutrient[];
};

export type Recipe = {
  id: string;
  family_id: string | null;
  scope: "shared" | "family";
  editable: boolean;
  recipe_key: string;
  name: string;
  description: string | null;
  suitable_meal_types: RecipeMealType[];
  yield_quantity: string | null;
  yield_unit: string | null;
  serving_count: string | null;
  source: string;
  is_active: boolean;
  ingredients: RecipeIngredient[];
  latest_composition: RecipeComposition | null;
  nutrition_issues: string[];
  created_at: string;
  updated_at: string;
};

export type RecipeIngredientWrite = {
  food_item_id: string;
  quantity: string;
  unit: string;
  preparation?: string | null;
  notes?: string | null;
};

export type RecipeCreate = {
  name: string;
  description?: string | null;
  suitable_meal_types: RecipeMealType[];
  yield_quantity?: string | null;
  yield_unit?: string | null;
  serving_count?: string | null;
  ingredients: RecipeIngredientWrite[];
};

export type RecipeUpdate = Partial<RecipeCreate> & {
  is_active?: boolean;
};
