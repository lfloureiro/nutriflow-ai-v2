import type { Person } from "./types";

export type Family = {
  id: string;
  name: string;
  timezone: string;
  created_at: string;
  updated_at: string;
};

export type FamilyCreate = {
  name: string;
  timezone: string;
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

export type PersonCreate = {
  first_name: string;
  last_name: string | null;
  birth_date: string;
  preferred_locale: string;
  timezone: string;
  energy_profile: PersonEnergyProfileCreate;
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

export type CreatedPerson = Person;
