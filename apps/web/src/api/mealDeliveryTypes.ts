export type MealDeliveryProviderKey = "uber_eats" | "glovo" | "bolt_food";

export type MealDeliveryMenuItem = {
  merchant_name: string;
  item_name: string;
  description: string | null;
  item_price: string;
  currency: string;
  delivery_fee: string | null;
  minimum_order: string | null;
  source_reference: string;
  energy_kcal: string | null;
  nutrition_evidence_level: "official" | "provider" | "estimated" | null;
  nutrition_confidence: string | null;
  eligible_for_nutrition_ranking: boolean;
};

export type MealDeliverySync = {
  provider_key: MealDeliveryProviderKey;
  observed_count: number;
  ingested: Array<{
    food_item_id: string;
    catalog_key: string;
    availability_id: string;
    offer_id: string;
    composition_id: string | null;
    eligible_for_nutrition_ranking: boolean;
  }>;
  items: MealDeliveryMenuItem[];
};
