export type FamilyMealDetailServing = {
  id: string;
  item_type: string;
  item_name: string;
  status: string;
  quantity_planned: string | null;
  quantity_served: string | null;
  quantity_consumed: string | null;
  quantity_unit: string | null;
  energy_planned_kcal: string | null;
  energy_served_kcal: string | null;
  energy_consumed_kcal: string | null;
};

export type FamilyMealDetailParticipant = {
  person_id: string;
  first_name: string;
  last_name: string | null;
  status: string;
  servings: FamilyMealDetailServing[];
};

export type FamilyMealDetail = {
  family_id: string;
  family_name: string;
  timezone: string;
  id: string;
  meal_type: string;
  title: string | null;
  scheduled_at: string;
  status: string;
  location: string | null;
  participants: FamilyMealDetailParticipant[];
};
