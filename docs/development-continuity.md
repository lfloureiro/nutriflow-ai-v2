# NutriFlow AI v2 development continuity

This is the handover entry point for NutriFlow AI v2. Repository code, migrations, tests, domain docs and ADRs are authoritative when conversation history differs.

## Product direction

NutriFlow AI v2 is standalone from v1. The primary operational chain is now implemented through shopping:

```text
Ingredients
-> Recipes
-> Recipe nutrition
-> Family plan
-> Person-specific portions
-> Pantry
-> Shopping
-> preferences / feedback
-> recommendation refinement
```

Family Home remains a lightweight orientation dashboard. Focused menus/screens are preferred over dense all-in-one screens.

## Core invariants

- Person remains the primary nutrition entity inside Family context;
- one shared MealEvent can have multiple MealParticipants;
- each participant has Person-specific Servings;
- normal meal planning uses exactly breakfast, lunch, snack and dinner;
- Food/Recipe composition is versioned and historical provenance is preserved;
- hard safety/mandatory nutrition rules run before preference/ranking signals;
- missing evidence is unknown, never silently zero;
- browser code presents server-authoritative nutrition/shopping/ranking evidence;
- user preference is separate from algorithmic nutrition/practical score;
- demo data is explicit and synthetic.

## Delivery workflow

Authoritative decision: `docs/decisions/ADR-007-development-workflow-and-ci.md`.

The user requested larger coherent integrations for speed. Safeguards remain mandatory:

1. resolve exact baseline SHA;
2. build code/tests/docs together;
3. run all relevant local gates on the exact final head;
4. warnings are failures;
5. open PR only after explicit local green confirmation;
6. verify GitHub Actions on the exact PR head;
7. verify mergeability/head unchanged;
8. guarded squash merge with expected head SHA;
9. verify resulting `main` SHA;
10. start the next block only from verified `main`.

## Last integrated checkpoint

PR #34, `Add core Family meal-planning foundation`, was squash-merged after local green confirmation and green API/Web CI.

```text
main SHA:    5e84364b451a887a1e2d09718fdea0db2109295b
schema head: d4f1a7c2e9b3
```

That integrated block includes:

- Family ingredient catalogue and versioned nutrition;
- Recipe CRUD/editor and deterministic Recipe nutrition;
- automatic Recipe recalculation after ingredient nutrition edits;
- fixed four meal types;
- editable Today/Week Family planner;
- Person-specific planned Servings;
- Pantry CRUD/UI;
- planned Recipe ingredient aggregation;
- quantity-aware stock subtraction;
- durable ShoppingList / ShoppingListItem lifecycle;
- simplified recommendation flow for one or several days;
- recommendation meal-type dropdown;
- cooked Recipe / delivery / restaurant source selection;
- automatic future DailyNutritionState materialization when recommendation needs it.

## Current large integration branch

```text
feature/recipe-preferences-recommendation-ranking
```

Baseline:

```text
5e84364b451a887a1e2d09718fdea0db2109295b
```

No database migration is required in this block; it reuses `FoodPreference`.

### Recipe ratings

Recipe ratings use:

```text
subject_type = recipe
subject_key = Recipe.recipe_key
preference_type = rating
intensity = 1..5
```

API:

```text
GET    /api/families/{family_id}/recipes/{recipe_id}/preferences
PUT    /api/families/{family_id}/recipes/{recipe_id}/preferences/{person_id}
DELETE /api/families/{family_id}/recipes/{recipe_id}/preferences/{person_id}
```

Rules:

- strict Family/Person/Recipe scope;
- one current rating per Person/Recipe at service level;
- update replaces the current rating and removes duplicate rating rows if encountered;
- clearing a rating is explicit;
- missing rating is neutral, not zero stars.

### Family preference UX

`Casa` now has:

```text
Receitas | Ingredientes | Despensa | Compras | Preferências
```

`Casa -> Preferências` is deliberately a separate focused screen:

- choose Recipe;
- rate 1..5 stars per Family member;
- see Family average and rating count;
- clear a Person rating.

The Recipe editor remains focused on definition and nutrition evidence.

### Recommendation ranking

Personal recipe rating contributes to the existing `preferences` score:

```text
1 star  -> -1.0
2 stars -> -0.5
3 stars ->  0.0
4 stars -> +0.5
5 stars -> +1.0
```

For practical recommendations, ratings from the other Family members contribute a separate smaller `family_preferences` signal:

```text
family score = ((average rating - 3) / 2) * 0.5
```

The selected Person is excluded from the Family average because their own rating already contributes through the stronger personal component.

Mandatory safety/nutrition exclusions are evaluated before these signals. A high rating can never restore an excluded candidate.

Runs with no rating signal retain `meal-recommendation-practical-v1`; runs where rating evidence participates use `meal-recommendation-practical-v2`. Family rating evidence used in the run is persisted in recommendation context.

See `docs/domain/recipe-preferences-and-ranking.md`.

## Validation for current branch

Expected test counts before local execution are approximately:

```text
API: 133 pytest tests
Web: 35 Vitest tests
```

Counts are expectations only until the exact final branch head passes locally.

No migration is expected, so validation is:

```powershell
cd D:\Python\nutriflow-ai-v2
python -m alembic check

cd apps\api
python -m ruff check .
python -m pytest -q

cd ..\web
npm install --no-package-lock --ignore-scripts
npm run test
npm run build
```

Do not open the PR until the exact final head is explicitly confirmed green locally.

## Deferred / next work

After ratings/preferences are integrated, the next large block should focus on feedback-driven planning rather than expanding dashboards. Candidate scope:

```text
accepted/rejected recommendation feedback
+ meal outcome feedback
+ repetition/fairness signal
+ recommendation explanation polish
+ plan/recommendation feedback loop
```

Broader limitations remain:

- Family UUID is still development context, not production authorization;
- production authentication/Family authorization is not implemented;
- DB-level MealEvent meal_type check remains future hardening;
- purchased ShoppingListItem does not automatically create PantryStockLot;
- npm lockfile / npm ci production hardening remains pending.

## Resume procedure

1. read this file, ADR-007 and relevant domain docs;
2. inspect exact `main`, active branch and schema head;
3. confirm local gate result on exact branch head;
4. never PR/merge an unvalidated head;
5. after merge verify exact new `main` before starting the next block.
