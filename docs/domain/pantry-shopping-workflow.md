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

1. persisted MealTransformationApplication operations are applied first when the planned meal is transformed;
2. a replace-ingredient operation contributes the persisted replacement FoodItem and replacement quantity/unit, never the source ingredient;
3. planned Serving quantity is converted to the Recipe yield unit when yield evidence exists;
4. that quantity becomes a Recipe batch multiplier;
5. effective ingredient quantities are multiplied by that factor;
6. all contributions are aggregated by FoodItem across all meals and people;
7. safely convertible units are normalized;
8. pantry stock is subtracted only after the Family-wide requirement is aggregated.

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

`Refeições -> Semana -> Aplicar semana` refreshes the same durable shopping list for the
Monday-Sunday planning interval after the weekly plan has been persisted. The refresh is deliberately
derivative rather than part of the weekly-plan transaction: if shopping recalculation fails, the week
remains saved and the browser reports the shopping failure separately instead of implying that weekly
materialization rolled back.

The Week view shows a compact post-apply summary with the number of automatically generated items
still needed and the number of planning requirements that could not be calculated safely.

## Correctness invariants

- Family isolation applies to stock and lists;
- pantry is subtracted after aggregate requirements are built;
- expired/inactive stock is not counted;
- unsafe units fail explicitly;
- missing calculation evidence is not treated as zero;
- shopping state is persisted independently from planner recalculation;
- transformed meals derive shopping requirements from persisted transformation provenance;
- missing or inconsistent transformation evidence fails shopping calculation explicitly rather than falling back to the source ingredient;
- weekly-plan persistence is not reported as failed merely because the derivative shopping refresh failed;
- browser code does not calculate authoritative shopping quantities.
