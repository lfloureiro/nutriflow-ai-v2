export type RestaurantDiscoveryPlace = {
  provider_place_id: string;
  name: string;
  cuisine: string[];
  amenity: string;
  address: string | null;
  latitude: string;
  longitude: string;
  website: string | null;
  phone: string | null;
  opening_hours: string | null;
  source_reference: string;
  primary_type: string | null;
  rating: string | null;
  rating_count: number | null;
  price_level: string | null;
  delivery: boolean | null;
  takeout: boolean | null;
  dine_in: boolean | null;
  serves_lunch: boolean | null;
  serves_dinner: boolean | null;
  serves_vegetarian_food: boolean | null;
  quality_score: string | null;
};

export type RestaurantDiscovery = {
  provider: string;
  area: string;
  observed_at: string;
  cached: boolean;
  attribution: string;
  restaurants: RestaurantDiscoveryPlace[];
};

export type RestaurantMenuItem = {
  restaurant_place_id: string;
  restaurant_name: string;
  item_name: string;
  description: string | null;
  item_price: string | null;
  currency: string;
  energy_kcal: string | null;
  nutrition_evidence_level: "official" | "provider" | "estimated" | null;
  nutrition_confidence: string | null;
  nutrition_basis_reference: string | null;
  source_reference: string;
  catalog_key: string | null;
  eligible_for_nutrition_ranking: boolean;
};

export type RestaurantMenu = {
  restaurant: RestaurantDiscoveryPlace;
  pages_scanned: string[];
  items: RestaurantMenuItem[];
  error: string | null;
};

export type RestaurantMenuSync = {
  provider: string;
  area: string;
  observed_at: string;
  menus: RestaurantMenu[];
  ingested_item_count: number;
  nutrition_ready_item_count: number;
};

export type RestaurantMenuSyncRequest = {
  area?: string | null;
  restaurant_limit?: number;
  item_limit_per_restaurant?: number;
};
