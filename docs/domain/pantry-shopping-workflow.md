# Pantry and shopping workflow

## Purpose

This workflow closes the operational chain from planned Family meals to actionable household shopping:

```text
Family meal plan
-> Person planned Recipe portions
-> Recipe ingredient requirements
-> aggregate by FoodItem
-> subtract usable PantryStockLot quantities
-> shopping shortages
-> durable ShoppingList
```

## Pantry stock

`PantryStockLot` remains the quantity-bearing stock entity. Normal Family CRUD now exposes:

```text
GET    /api/families/{family_id}/pantry
POST   /api/families/{family_id}/pantry
PATCH  /api/families/{family_id}/pantry/{lot_id}
DELETE /api/families/{family_id}/pantry/{lot_id}
```

Delete is a soft availability change. Historical lot identity is preserved.

Each lot keeps:

- FoodItem identity;
- quantity and unit;
- optional household location;
- optional expiry instant;
- observed timestamp;
- available/inactive state;
- source/provenance.

Expired or inactive lots do not satisfy plan requirements.

## Plan aggregation

Shopping calculation uses planned/prepared MealEvents in the selected Family-local date range.

For each Person Serving referencing a Recipe:

1. planned Serving quantity is converted to the Recipe yield unit when yield evidence exists;
2. that quantity becomes a Recipe batch multiplier;
3. RecipeIngredient quantities are multiplied by that factor;
4. all contributions are aggregated by FoodItem across all meals and people;
5. safely convertible units are normalized;
6. pantry stock is subtracted only after the Family-wide requirement is aggregated.

This ordering is important. Evaluating each meal independently could incorrectly spend the same pantry stock multiple times.

When a Recipe cannot be safely scaled, or ingredient/stock units are incompatible, the issue is returned explicitly. No density or unsafe conversion is guessed.

## Durable shopping list

New persisted entities:

- `ShoppingList`;
- `ShoppingListItem`.

The active list stores its last planning range and generation time. Items are either:

- `automatic` — generated from current plan shortages;
- `manual` — household items entered directly by the user.

Item status is:

- `needed`;
- `purchased`.

Automatic refresh updates currently needed automatic items while preserving manual items. Purchased automatic items are retained as checked history rather than silently deleted.

API:

```text
GET    /api/families/{family_id}/shopping-list
POST   /api/families/{family_id}/shopping-list/refresh
POST   /api/families/{family_id}/shopping-list/items
PATCH  /api/families/{family_id}/shopping-list/items/{item_id}
DELETE /api/families/{family_id}/shopping-list/items/{item_id}
```

## UI

`Casa` now exposes four focused destinations:

```text
Receitas
Ingredientes
Despensa
Compras
```

`Despensa` is a stock list/editor rather than a dashboard.

`Compras` shows:

- selected planning interval;
- calculated requirement;
- usable pantry stock;
- missing quantity;
- durable shopping items;
- manual items;
- purchased checkbox;
- quantity/name adjustments;
- explicit calculation issues.

## Correctness invariants

- Family isolation applies to stock and lists;
- pantry is subtracted after aggregate requirements are built;
- expired/inactive stock is not counted;
- unsafe units fail explicitly;
- missing calculation evidence is not treated as zero;
- shopping state is persisted independently from planner recalculation;
- browser code does not calculate authoritative shopping quantities.
