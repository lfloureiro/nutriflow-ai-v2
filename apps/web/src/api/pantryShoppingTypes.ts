export type PantryLot = {
  id: string;
  family_id: string;
  food_item_id: string;
  food_item_name: string;
  stock_key: string;
  quantity_available: string;
  unit: string;
  location: string | null;
  expires_at: string | null;
  observed_at: string;
  is_available: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type PantryLotCreate = {
  food_item_id: string;
  quantity_available: string;
  unit: string;
  location?: string | null;
  expires_at?: string | null;
  notes?: string | null;
};

export type PantryLotUpdate = {
  quantity_available?: string;
  unit?: string;
  location?: string | null;
  expires_at?: string | null;
  is_available?: boolean;
  notes?: string | null;
};

export type PlannedRequirement = {
  food_item_id: string;
  food_item_name: string;
  required_quantity: string;
  available_quantity: string;
  missing_quantity: string;
  unit: string;
};

export type ShoppingListItem = {
  id: string;
  food_item_id: string | null;
  name: string;
  quantity: string | null;
  unit: string | null;
  item_source: "automatic" | "manual";
  status: "needed" | "purchased";
  notes: string | null;
  sort_order: number;
};

export type ShoppingList = {
  id: string;
  family_id: string;
  title: string;
  status: "active" | "archived";
  planning_start: string | null;
  planning_end: string | null;
  generated_at: string | null;
  requirements: PlannedRequirement[];
  planning_issues: string[];
  items: ShoppingListItem[];
  created_at: string;
  updated_at: string;
};

export type ShoppingListItemCreate = {
  name: string;
  quantity?: string | null;
  unit?: string | null;
  notes?: string | null;
};

export type ShoppingListItemUpdate = {
  name?: string;
  quantity?: string | null;
  unit?: string | null;
  status?: "needed" | "purchased";
  notes?: string | null;
};
