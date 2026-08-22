export type IngredientNutrient = {
  key: string;
  value: string;
  unit: string;
};

export type IngredientComposition = {
  id: string;
  reference_quantity: string;
  reference_unit: string;
  energy_kcal: string | null;
  data_version: string;
  source: string;
  source_reference: string | null;
  effective_at: string;
  notes: string | null;
  nutrients: IngredientNutrient[];
};

export type Ingredient = {
  id: string;
  family_id: string;
  catalog_key: string;
  name: string;
  brand: string | null;
  description: string | null;
  source: string;
  is_active: boolean;
  latest_composition: IngredientComposition | null;
  created_at: string;
  updated_at: string;
};

export type IngredientNutrientWrite = {
  key: string;
  value: string;
  unit: string;
};

export type IngredientCompositionWrite = {
  reference_quantity: string;
  reference_unit: string;
  energy_kcal: string | null;
  nutrients: IngredientNutrientWrite[];
  notes?: string | null;
};

export type IngredientCreate = {
  name: string;
  brand?: string | null;
  description?: string | null;
  composition?: IngredientCompositionWrite | null;
};

export type IngredientUpdate = {
  name?: string;
  brand?: string | null;
  description?: string | null;
  is_active?: boolean;
  composition?: IngredientCompositionWrite | null;
};
