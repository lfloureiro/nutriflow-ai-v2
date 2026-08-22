# Family ingredient catalogue workflow

## Purpose

Ingredients are first-class reusable Family assets. They are the base of the operational NutriFlow chain:

```text
Ingredient -> Recipe -> Meal plan -> Pantry requirement -> Shopping requirement
```

This increment exposes the existing `FoodItem` / `FoodCompositionSnapshot` model through a normal API and web workflow.

## Scope

A Family can now:

- list its ingredients;
- search by ingredient name or brand;
- create an ingredient;
- edit name, brand and description;
- add a nutrition composition;
- replace current nutrition evidence by creating a new composition version;
- deactivate an ingredient without deleting historical/reference data;
- include inactive ingredients in catalogue administration and reactivate them.

Only Family-owned `FoodItem` records with `food_kind=ingredient` are managed by this workflow. Shared/system/provider catalogue entries remain a later concern.

## API

```text
GET    /api/families/{family_id}/ingredients
POST   /api/families/{family_id}/ingredients
GET    /api/families/{family_id}/ingredients/{ingredient_id}
PATCH  /api/families/{family_id}/ingredients/{ingredient_id}
DELETE /api/families/{family_id}/ingredients/{ingredient_id}
```

List filters:

```text
q=<name-or-brand>
include_inactive=true|false
```

`DELETE` is deliberately a soft-delete operation: it sets `is_active=false`. Existing recipes and historical Servings must not be broken by catalogue cleanup.

## Nutrition composition

Manual composition input records:

- positive reference quantity;
- reference unit;
- optional energy kcal;
- zero or more named nutrient values/units;
- optional notes.

The initial editor exposes common fields useful for recipe planning:

- energy;
- protein;
- carbohydrate;
- fat;
- fibre (`fiber` key);
- sodium.

The persisted model remains extensible through `FoodNutrientComponent`; the UI list is not a domain limit.

## Versioning rule

Nutrition corrections never mutate an older `FoodCompositionSnapshot`.

On a nutrition edit the API creates a new manual snapshot with:

```text
data_version = manual-<uuid>
source = user
source_reference = nutriflow-family-editor
```

The catalogue read model returns the latest composition for everyday editing/display. Older snapshots remain available in the database for historical provenance and later recipe/Serving reproducibility.

## Validation and authority

The API validates:

- non-empty ingredient name;
- positive reference quantity;
- non-negative energy/nutrient values;
- non-empty units;
- unique nutrient keys within one composition;
- Family ownership for every read/write action.

The browser does not calculate authoritative nutrition. It collects manual evidence and sends it to the API. Recipe composition and Serving nutrition are later deterministic server calculations.

## UX

`Casa` now opens the ingredient catalogue instead of a placeholder.

The interaction uses progressive disclosure:

```text
Ingredientes list/search
  -> Novo ingrediente
  -> Editar ingrediente
```

The list shows only identity plus the latest reference quantity/energy summary. The editor owns descriptive and nutrition fields. This follows the product preference for more focused screens rather than a dense all-in-one catalogue grid.

## Explicit limitations

This increment does not yet:

- import nutrition from an external provider;
- use AI to identify/match an ingredient;
- calculate Recipe composition;
- expose Recipe CRUD;
- aggregate pantry/shopping requirements;
- provide destructive hard-delete.

Those are subsequent increments built on this catalogue.
