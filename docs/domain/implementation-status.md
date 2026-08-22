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

The integrated domain already includes Family/Person, MealEvent/MealParticipant/Serving, Food/Recipe composition snapshots, deterministic Serving nutrition, nutrition/health state, safety-first recommendations, pantry-stock logic and Family-first shell/Home/Person/meal-map read views.

## Current large integration

```text
feature/core-meal-planning-foundation
```

This branch intentionally combines several tightly connected increments so the product reaches a usable meal-planning loop faster.

### Ingredient catalogue

Implemented:

- Family-scoped ingredient list/search/create/update;
- versioned nutrition composition;
- energy, protein, carbohydrate, fat, fibre and sodium editor;
- ingredient nutrition edits automatically recalculate referencing Family Recipes;
- inactive/reactivate lifecycle rather than destructive deletion;
- responsive `Casa -> Ingredientes` workflow.

### Recipe catalogue

Implemented:

- Family-scoped Recipe list/search/create/update/deactivate/reactivate;
- ordered RecipeIngredient editing;
- quantity/unit/preparation fields;
- serving count and finished yield;
- responsive `Casa -> Receitas` default workflow.

### Recipe nutrition

Implemented `recipe-nutrition-v1`:

- scales current ingredient composition snapshots using safe unit conversion;
- creates a new RecipeCompositionSnapshot for every nutrition-relevant Recipe change and referenced ingredient-composition update;
- stores ingredient snapshot/version provenance;
- calculates total energy and per-serving energy when evidence permits;
- calculates nutrient totals/per-serving values only with complete compatible evidence;
- records missing composition, missing energy/nutrient evidence and unsafe conversion issues;
- never treats missing evidence as zero;
- never silently falls back to stale Recipe nutrition after the Recipe or ingredient evidence changes.

### Four meal types

Shared server request contract now limits normal meal types to:

```text
breakfast
lunch
snack
dinner
```

This is used by the new Family planner plus existing recommendation request APIs.

### Editable Family meal plan

Implemented:

- Family-local 1..14 day read model;
- exactly four slots for every day including empty slots;
- create planned Recipe MealEvent;
- choose Family participants;
- explicit or Recipe-derived default Person portions;
- deterministic Recipe Serving nutrition per participant;
- edit planned date/time/type/Recipe/participants/portions/location/notes;
- cancel planned meal rather than destructive deletion;
- prepared/served/completed events locked from planning edits;
- Today/Week web planner with Add/Edit/Remove;
- existing recommendation workflow preserved under `Recomendar`.

## Expected validation

Before local execution, expected counts are:

```text
API: 121 pytest tests
Web: 27 Vitest tests
```

Also required:

- `alembic check` clean;
- Ruff clean;
- strict TypeScript/Vite production build clean;
- no warnings treated as acceptable failures.

There is no new migration in this integration. Existing catalogue/MealEvent schema is reused. The fixed meal-type rule is enforced at all current user-facing server write/request boundaries; a future DB check constraint remains hardening, not required for the product workflow itself.

## Core operational chain after this branch

Once locally validated, CI-green and merged, NutriFlow has this product path:

```text
Ingredient
-> Recipe
-> calculated Recipe nutrition
-> four-slot Family plan
-> shared MealEvent
-> Person-specific Serving
```

## Next large block

Next priority:

```text
Pantry CRUD/UI
+ aggregate planned Recipe ingredient requirements
+ subtract quantity-aware stock
+ shopping requirements
+ durable ShoppingList lifecycle/UI
```

After that:

- Recipe/Person ratings and Family aggregate preference;
- integrate preference + nutrition fit + pantry/practical context into recommendation score;
- secondary Person analytics/health detail;
- authentication/authorization and deployment hardening.

## Safety/correctness invariants

Preserve:

- hard adverse-reaction/mandatory constraints before ranking;
- missing mandatory evidence fails closed where required;
- unsafe conversions rejected, no inferred density;
- versioned composition provenance;
- historical Servings not rewritten by catalogue changes;
- Family isolation;
- missing evidence never zero-filled;
- browser does not author nutrition calculations or safety decisions;
- warnings are failures.

## Deferred branch

`feature/web-family-meal-detail` remains unmerged. Its detailed Serving presentation may be reused later, but it no longer blocks the operational meal-planning foundation.
