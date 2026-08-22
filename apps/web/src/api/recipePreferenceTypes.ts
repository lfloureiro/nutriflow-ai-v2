export type PersonRecipeRating = {
  person_id: string;
  first_name: string;
  last_name: string | null;
  rating: number;
  notes: string | null;
  updated_at: string;
};

export type RecipePreferenceSummary = {
  recipe_id: string;
  average_rating: string | null;
  rating_count: number;
  ratings: PersonRecipeRating[];
};

export type RecipeRatingWrite = {
  rating: number;
  notes?: string | null;
};
