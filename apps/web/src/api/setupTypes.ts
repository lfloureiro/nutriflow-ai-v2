import type { Person } from "./types";

export type MealDiscoverySource =
  | "shared_recipes"
  | "uber_eats"
  | "glovo"
  | "bolt_food"
  | "restaurants";

export type MealDiscoveryCapabilityStatus =
  | "ready"
  | "needs_configuration"
  | "integration_required"
  | "disabled";

export type MealDiscoveryCapability = {
  source: MealDiscoverySource;
  selected: boolean;
  supported: boolean;
  live: boolean;
  status: MealDiscoveryCapabilityStatus;
  detail: string;
};

export type MealDiscoveryCapabilities = {
  capabilities: MealDiscoveryCapability[];
};

export type Family = {
  id: string;
  name: string;
  timezone: string;
  meal_discovery_sources: MealDiscoverySource[];
  delivery_address: string | null;
  restaurant_area: string | null;
  created_at: string;
  updated_at: string;
};

export type FamilyCreate = {
  name: string;
  timezone: string;
  meal_discovery_sources: MealDiscoverySource[];
  delivery_address: string | null;
  restaurant_area: string | null;
};

export type FamilyUpdate = Partial<Omit<FamilyCreate, "name" | "timezone">> & {
  name?: string;
  timezone?: string;
};

export type ActivityLevel = "sedentary" | "light" | "moderate" | "active" | "very_active";
export type EnergyCalculationSex = "male" | "female";
export type NutritionGoalType = "maintain" | "lose" | "gain";

export type PersonEnergyProfileCreate = {
  sex_for_energy_calculation: EnergyCalculationSex;
  height_cm: string;
  weight_kg: string;
  activity_level: ActivityLevel;
  goal_type: NutritionGoalType;
  target_rate_kg_per_week: string | null;
  standard_breakfast_kcal: string;
};

export type PersonMealDiscoveryCreate = {
  meal_discovery_sources: MealDiscoverySource[] | null;
  delivery_address: string | null;
  restaurant_area: string | null;
};

export type PersonMealDiscoveryUpdate = PersonMealDiscoveryCreate & {
  inherit_family_defaults: boolean;
};

export type PersonCreate = {
  first_name: string;
  last_name: string | null;
  birth_date: string;
  preferred_locale: string;
  timezone: string;
  energy_profile: PersonEnergyProfileCreate;
  meal_discovery?: PersonMealDiscoveryCreate | null;
};

export type PersonEnergyProfile = {
  person_id: string;
  sex_for_energy_calculation: EnergyCalculationSex;
  activity_level: ActivityLevel;
  standard_breakfast_kcal: string;
  height_cm: string;
  weight_kg: string;
  goal_type: NutritionGoalType;
  target_rate_kg_per_week: string | null;
  estimated_bmr_kcal: string;
  estimated_tdee_kcal: string;
  energy_min_kcal: string;
  energy_max_kcal: string;
  calculation_version: string;
};

export type PersonMealDiscovery = {
  person_id: string;
  inherits_family_defaults: boolean;
  meal_discovery_sources: MealDiscoverySource[];
  delivery_address: string | null;
  restaurant_area: string | null;
};

export type CreatedPerson = Person;
