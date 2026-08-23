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
};

export type RestaurantDiscovery = {
  provider: string;
  area: string;
  observed_at: string;
  cached: boolean;
  attribution: string;
  restaurants: RestaurantDiscoveryPlace[];
};
