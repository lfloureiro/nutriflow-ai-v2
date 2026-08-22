# NutriFlow AI v2 development continuity

This is the handover entry point for NutriFlow AI v2. Repository code, migrations, tests, domain/vision docs and ADRs are authoritative when conversation history differs.

## Product direction

NutriFlow AI v2 is standalone from v1. The primary operational chain is:

```text
Ingredients
-> Recipes
-> Recipe nutrition
-> Family plan
-> Person-specific portions
-> Pantry
-> Shopping
-> history / feedback
```

Family Home remains a lightweight orientation dashboard. Detailed health/analytics work is secondary until the operational meal-planning chain is usable.

## Core invariants

- Person remains the primary nutrition entity inside Family context;
- one shared MealEvent can have multiple MealParticipants;
- each participant has Person-specific Servings;
- normal meal planning uses exactly breakfast, lunch, snack and dinner;
- Food/Recipe composition is versioned and historical provenance is preserved;
- hard safety/mandatory nutrition rules run before ranking/ML;
- missing evidence is unknown, never silently zero;
- browser code presents server-authoritative nutrition/shopping state;
- catalogue cleanup does not destructively break historical meal evidence;
- demo data is explicit, synthetic and never auto-seeded.

## Delivery workflow

Authoritative decision: `docs/decisions/ADR-007-development-workflow-and-ci.md`.

The user requested larger integrations for speed. We therefore use larger coherent functional blocks while retaining exact-head safeguards:

1. build code, migration, tests and docs together;
2. run all relevant local gates on the exact final head;
3. warnings are failures;
4. PR only after explicit local green confirmation;
5. CI must pass on the exact PR head;
6. confirm mergeability and unchanged head;
7. guarded squash merge;
8. verify resulting `main` before the next branch.

## Last integrated checkpoint

```text
main SHA:    e0bdd8a9c8cc40f58ab67f14727ab134ac2156dc
schema head: a7c4e9f2b6d1
API tests:   110
Web tests:   19
```

PR #33 is the last integrated PR on that baseline.

## Current large integration branch

```text
feature/core-meal-planning-foundation
```

This branch contains the complete operational foundation from integrated `main`.

### 1. Ingredients

- Family ingredient list/search/create/edit;
- versioned FoodCompositionSnapshot evidence;
- nutrition edits automatically recalculate Family Recipes that reference the ingredient;
- deactivate/reactivate rather than destructive delete;
- `Casa -> Ingredientes` UI.

### 2. Recipes and recipe nutrition

- Family Recipe CRUD/search/deactivate/reactivate;
- ordered RecipeIngredient editor;
- quantities, units, preparation, servings and yield;
- deterministic `recipe-nutrition-v1` calculation;
- new RecipeCompositionSnapshot on nutrition-relevant changes;
- total and per-serving energy/nutrients;
- explicit missing/unsafe/incomplete evidence issues;
- no client-side authoritative nutrition calculation.

### 3. Four fixed meal types

Shared server contract:

```text
breakfast
lunch
snack
dinner
```

Planner and recommendation request APIs reject arbitrary normal meal-type strings.

### 4. Editable Family meal plan

API:

```text
GET    /api/families/{family_id}/meal-plan
POST   /api/families/{family_id}/meal-plan
PATCH  /api/families/{family_id}/meal-plan/{meal_event_id}
DELETE /api/families/{family_id}/meal-plan/{meal_event_id}
```

Capabilities:

- Family-local Today/Week ranges;
- four visible slots every day including empty slots;
- planned Recipe MealEvents;
- Family participants;
- Person-specific planned quantities;
- Recipe-derived default portions;
- server-side Serving nutrition;
- edit/replace/cancel while planned;
- prepared/served/completed meals locked from planner editing.

### 5. Pantry

Existing `PantryStockLot` is now exposed as a normal Family workflow:

```text
GET    /api/families/{family_id}/pantry
POST   /api/families/{family_id}/pantry
PATCH  /api/families/{family_id}/pantry/{lot_id}
DELETE /api/families/{family_id}/pantry/{lot_id}
```

- quantity/unit/location/expiry;
- active/inactive stock lifecycle;
- strict Family scoping;
- expired/inactive stock does not satisfy plan requirements;
- `Casa -> Despensa` UI.

### 6. Planned requirements and durable shopping list

Planned Servings are converted into Recipe batch multipliers, RecipeIngredient requirements are aggregated across all people/meals in the chosen interval, and only then is pantry stock subtracted.

This prevents the same pantry quantity being consumed independently by multiple planned meals.

New persisted domain:

```text
ShoppingList
-> ShoppingListItem
```

Migration head on this branch:

```text
d4f1a7c2e9b3
```

API:

```text
GET    /api/families/{family_id}/shopping-list
POST   /api/families/{family_id}/shopping-list/refresh
POST   /api/families/{family_id}/shopping-list/items
PATCH  /api/families/{family_id}/shopping-list/items/{item_id}
DELETE /api/families/{family_id}/shopping-list/items/{item_id}
```

- automatic shortage items generated from the plan;
- manual household items;
- needed/purchased state;
- quantity/name adjustments;
- purchased automatic items retained as checked history;
- explicit planning/conversion issues;
- `Casa -> Compras` UI shows required / stock / missing evidence.

See `docs/domain/pantry-shopping-workflow.md`.

## Web information architecture in this branch

`Casa`:

```text
Receitas | Ingredientes | Despensa | Compras
```

`Refeições`:

```text
Hoje | Semana | Recomendar
```

Screens remain task-focused rather than dashboard-heavy.

## Current validation state

The previous local run reached:

```text
115 existing API tests passing
6 Recipe/planner tests failing from SQLAlchemy autoflush warning
```

That warning has since been fixed by attaching a new Recipe to the Session before ingredient-resolution queries trigger autoflush. The fix has not yet received a local rerun because the user asked to add the Pantry + Shopping block first.

With the new block, expected counts before local execution are:

```text
API: 125 pytest tests
Web: 30 Vitest tests
```

These are expectations only until the exact final branch head is locally validated.

Because this block adds a migration, local validation must include upgrade/current/check:

```powershell
cd D:\Python\nutriflow-ai-v2
python -m alembic upgrade head
python -m alembic current
python -m alembic check

cd apps\api
python -m ruff check .
python -m pytest -q

cd ..\web
npm install --no-package-lock --ignore-scripts
npm run test
npm run build
```

Expected schema head after upgrade:

```text
d4f1a7c2e9b3
```

Do not open the PR until the exact final branch head is explicitly confirmed green locally.

## Deferred work preserved

`feature/web-family-meal-detail` remains unmerged. Its detailed Serving presentation can be reused later, but it no longer blocks the operational planning flow.

## Demo

Fixed Family ID:

```text
11111111-1111-4111-8111-111111111111
```

The demo does not auto-seed the new ingredient/Recipe/Pantry/Shopping workflows; normal UI creation deliberately acts as the smoke test.

## Next large block after this branch merges

Recommended next block:

```text
Recipe/Person ratings
+ Family aggregate preference
+ preference history
+ integrate preference into recommendation/planning score
+ feedback loop
```

Keep user rating separate from algorithmic score.

## Known broader limitations

- Family UUID remains development context, not production authorization;
- production authentication/Family authorization is not implemented;
- DB-level MealEvent `meal_type` check constraint remains future hardening; current write APIs enforce the fixed contract;
- purchasing an item does not automatically create/update a PantryStockLot; stock remains an explicit household observation;
- recipe preference/rating UX is not yet implemented;
- npm lockfile / `npm ci` production hardening remains pending.

## Resume procedure

1. read this file, ADR-007 and core meal-planning docs;
2. inspect exact `main`, active branch and migration head;
3. confirm exact final branch head and local gate result;
4. never PR/merge an unvalidated head;
5. after merge verify exact new `main` before starting ratings/preferences.
