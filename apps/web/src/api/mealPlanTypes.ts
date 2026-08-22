export type MealType = "breakfast" | "lunch" | "snack" | "dinner";

export type MealPlanParticipant = {
  person_id: string;
  first_name: string;
  last_name: string | null;
  quantity: string | null;
  unit: string | null;
  energy_kcal: string | null;
};

export type MealPlanEntry = {
  id: string;
  meal_type: MealType;
  title: string | null;
  scheduled_at: string;
  local_time: string;
  status: string;
  recipe_id: string | null;
  recipe_name: string | null;
  location: string | null;
  notes: string | null;
  participants: MealPlanParticipant[];
};

export type MealPlanSlot = {
  meal_type: MealType;
  meals: MealPlanEntry[];
};

export type MealPlanDay = {
  date: string;
  slots: MealPlanSlot[];
};

export type FamilyMealPlan = {
  family_id: string;
  family_name: string;
  timezone: string;
  start_date: string;
  end_date: string;
  days: MealPlanDay[];
};

export type MealPlanParticipantWrite = {
  person_id: string;
  quantity?: string | null;
  unit?: string | null;
};

export type MealPlanEntryCreate = {
  date: string;
  meal_type: MealType;
  local_time: string;
  recipe_id: string;
  participants: MealPlanParticipantWrite[];
  location?: string | null;
  notes?: string | null;
};

export type MealPlanEntryUpdate = Partial<MealPlanEntryCreate>;
