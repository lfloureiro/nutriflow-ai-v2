# Domain implementation status

`docs/development-continuity.md` is the handover entry point. This file summarizes current capability and active delivery.

## Integrated baseline

Integrated through PR #33:

```text
main SHA:    e0bdd8a9c8cc40f58ab67f14727ab134ac2156dc
schema head: a7c4e9f2b6d1
API tests:   110
Web tests:   19
```

## Current large integration

```text
feature/core-meal-planning-foundation
```

This branch intentionally combines the tightly connected operational meal-planning chain.

### Ingredients

- Family-scoped list/search/create/update;
- versioned nutrition evidence;
- common nutrition editor;
- referenced Recipes recalculate after ingredient nutrition changes;
- deactivate/reactivate lifecycle;
- `Casa -> Ingredientes`.

### Recipes and nutrition

- Recipe CRUD/search/lifecycle;
- ordered RecipeIngredient editing;
- quantity/unit/preparation/servings/yield;
- deterministic `recipe-nutrition-v1`;
- versioned RecipeCompositionSnapshot provenance;
- total/per-serving nutrition;
- explicit incomplete/unsafe evidence issues;
- `Casa -> Receitas`.

### Four-slot Family planner

Normal meal types are fixed to:

```text
breakfast
lunch
snack
dinner
```

The planner provides:

- 1..14 Family-local days;
- four slots per day even when empty;
- Recipe MealEvents;
- Family participants;
- Person-specific planned Serving quantities;
- deterministic planned nutrition;
- edit/replace/cancel while planned;
- Today/Week UI plus existing recommendation flow.

### Pantry

Existing `PantryStockLot` now has normal Family CRUD/UI:

- FoodItem identity;
- quantity/unit;
- optional location and expiry;
- active/inactive lifecycle;
- strict Family isolation;
- expired/inactive stock excluded from sufficiency;
- `Casa -> Despensa`.

### Planned requirements

For a selected planning interval:

1. planned Person Recipe Servings are converted to Recipe batch multipliers;
2. RecipeIngredient quantities are aggregated across all people and meals;
3. compatible units are normalized safely;
4. pantry stock is subtracted once from the aggregate requirement;
5. missing quantities become shopping shortages.

Unsafe or incomplete scaling remains an explicit issue and is never guessed/zero-filled.

### Durable shopping list

New persisted models:

```text
ShoppingList
ShoppingListItem
```

Current migration head:

```text
d4f1a7c2e9b3
```

Capabilities:

- active Family shopping list;
- automatic items generated from plan shortages;
- manual items;
- needed/purchased lifecycle;
- quantity/name adjustment;
- purchased automatic items retained as checked history;
- planning range and generation evidence;
- `Casa -> Compras` with required / stock / missing display.

See `docs/domain/pantry-shopping-workflow.md`.

## Expected validation

The previous local run had 115 existing API tests passing and six new Recipe/planner tests blocked by one SQLAlchemy autoflush warning. That warning has since been corrected by adding new Recipe objects to the Session before ingredient lookup queries.

After Pantry + Shopping, expected counts before the next local run are:

```text
API: 125 pytest tests
Web: 30 Vitest tests
```

Required gates now include migration execution:

```text
alembic upgrade head
alembic current -> d4f1a7c2e9b3
alembic check clean
Ruff clean
API tests clean
Web tests clean
strict TypeScript/Vite build clean
```

Counts are expectations until validated on the exact final head.

## Operational chain after this branch

```text
Ingredient
-> Recipe
-> calculated Recipe nutrition
-> four-slot Family plan
-> Person Serving portions
-> aggregate ingredient requirements
-> Pantry subtraction
-> durable ShoppingList
```

## Next large block

After merge, the next logical block is:

```text
Recipe/Person ratings
+ Family aggregate preference
+ preference history
+ planning/recommendation score integration
+ feedback loop
```

User rating must remain distinct from algorithmic recommendation score.

## Safety/correctness invariants

Preserve:

- hard adverse-reaction/mandatory constraints before ranking;
- missing mandatory evidence fails closed where required;
- unsafe conversions rejected, no inferred density;
- versioned nutrition provenance;
- historical Servings not rewritten by catalogue changes;
- Family isolation;
- aggregate requirements before pantry subtraction;
- missing evidence never zero-filled;
- browser does not author nutrition/shopping calculations;
- warnings are failures.

## Deferred branch

`feature/web-family-meal-detail` remains unmerged. Its detailed Serving presentation may be reused later but does not block the operational flow.
