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
