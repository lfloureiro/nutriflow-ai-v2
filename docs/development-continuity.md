# NutriFlow AI v2 development continuity

This is the handover entry point for NutriFlow AI v2. Repository code, migrations, tests, domain docs and ADRs are authoritative when conversation history differs.

## Product direction

NutriFlow AI v2 is standalone from v1. The implemented operational chain now covers:

```text
Family / Persons
-> Ingredients
-> Recipes
-> versioned nutrition evidence
-> Family meal plan
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
- anthropometric history is append-only when a measurement actually changes;
- hard safety/mandatory nutrition rules run before preference/ranking signals;
- missing evidence is unknown, never silently zero;
- browser code presents server-authoritative nutrition/shopping/ranking evidence;
- user preference is separate from algorithmic nutrition/practical score;
- shared catalogue entities are visible to Families but remain read-only unless explicitly owned by that Family;
- demo or synthetic evidence must remain explicitly identified and must not be presented as real measured/curated nutrition;
- persisted timezone values must be valid IANA timezone names.

## Delivery workflow

Authoritative decision: `docs/decisions/ADR-007-development-workflow-and-ci.md`.

The user requested larger coherent integrations for speed. Safeguards remain mandatory:

1. resolve exact baseline SHA;
2. build code/tests/docs together;
3. run all relevant local gates on the exact final head;
4. warnings are failures;
5. open a PR only after explicit local green confirmation;
6. verify GitHub Actions on the exact PR head;
7. verify mergeability/head unchanged;
8. guarded merge with expected head SHA;
9. verify resulting `main` SHA;
10. start the next block only from verified `main`.

Never use `docker compose down -v` as a routine smoke-test reset. The development PostgreSQL volume may contain local user-created data.

## Last verified `main` checkpoint

The branch preceding this work was fast-forwarded cleanly into `main`.

```text
main baseline for this branch:
8f8ddf74698adf708caa73ee1af11b774eeca576
```

That baseline already includes the Family-first shell, ingredient/recipe/pantry/shopping flow, Family meal planning, preference-aware recommendations, feedback learning, structural meal suitability and calorie-aware planning refinements.

## Current integration branch

```text
feature/family-catalog-and-profile-editing
```

Baseline:

```text
8f8ddf74698adf708caa73ee1af11b774eeca576
```

No database migration is currently required by this branch. It reuses existing Family, PersonProfile, AnthropometricMeasurement, NutritionGoal, NutritionTarget, FoodItem and Recipe structures.

The branch passed API/Web CI at checkpoint `147d8dbffb392a6602407d5f7cd4b0f41a22ed1b`. Additional autonomous catalogue-quality and integration-UX work was added after that checkpoint, so the **final branch head must be revalidated** before smoke testing or integration.

### Family editing

`Mais` now exposes focused Family settings for:

- Family name;
- IANA timezone;
- meal-discovery sources;
- delivery address;
- restaurant area.

The existing Family PATCH API remains authoritative and the shell dashboard is refreshed after a successful save.

The screen also shows installation capability for each meal-discovery source. Selection and live capability are intentionally separate concepts: selecting a source does not imply that credentials, consumer access or a provider adapter exist.

### Person editing and energy-profile history

`Pessoas -> Perfil` now supports editing:

- first/last name;
- birth date;
- IANA timezone;
- sex used for energy calculation;
- height and weight;
- habitual activity level;
- maintain/lose/gain goal and weekly rate;
- standard breakfast energy.

Rules:

- identity-only changes do not create a new energy target;
- birth date, timezone or an actual energy input change triggers recalculation when a complete energy profile exists;
- a recalculation supersedes the prior active NutritionGoal/NutritionTarget instead of deleting history;
- height/weight measurements are appended only when the corresponding value actually changes;
- Person meal-discovery overrides remain intact when the energy profile is updated;
- the Family dashboard is refreshed after Person edits so names/timezones do not remain stale in the list or shell.

### Shared ingredient catalogue

The Family ingredient catalogue now returns:

```text
Family-owned ingredients
+ shared ingredients (family_id IS NULL)
```

Read models expose explicit `scope` and `editable` fields. Shared ingredients are visible in `Casa -> Ingredientes`, can be used by Family recipes, and render as read-only rows. Family CRUD endpoints still reject writes to shared catalogue rows.

Each Ingredient read also exposes `recipe_usage_count`: the number of active Recipes visible to this Family that use the Ingredient. A Family never sees private Recipe usage from another Family.

The Ingredient screen remains deliberately lightweight but now exposes nutrition-quality filters:

```text
all
with energy
composition present but energy missing
composition missing
```

A compact summary shows total Ingredients, how many have energy, and how many still need enrichment.

### Recipe nutrition readiness and provenance

Recipe ingredient reads distinguish:

```text
has_nutrition
has_energy
```

This lets the Recipe UI identify the exact Ingredient blocking an energy calculation rather than only displaying a generic missing-evidence error.

Every Recipe composition returned by the catalogue API also has an explicit evidence class:

```text
ingredient_calculated
synthetic_development
imported
unknown
```

The deterministic Recipe nutrition rule remains fail-closed:

- energy is calculated only when every Recipe Ingredient has usable composition/energy evidence and safe unit conversion;
- missing composition stays explicit;
- composition without energy stays explicit;
- unsafe unit conversion stays explicit;
- stale nutrition is never silently reused after Recipe definition changes.

`Casa -> Receitas` exposes quality filters for calculated, incomplete and development-estimate Recipes. Recipe detail lists the exact blocking Ingredients and unit-conversion problems.

### Legacy v1 nutrition policy

The real v1 snapshot contains Ingredient names and Recipe quantities but does not contain trustworthy Ingredient nutrition compositions.

Therefore:

- v1 structure may be imported;
- absent nutrition must not be fabricated as production evidence;
- existing development-only synthetic Recipe nutrition remains demo evidence only and is explicitly classified as `synthetic_development`;
- synthetic Recipe calories are visibly labelled as development estimates and are not presented as equivalent to Ingredient-calculated nutrition;
- a future catalogue-enrichment/import path must preserve source, source reference, effective date and data version for each FoodCompositionSnapshot.

See `docs/domain/family-catalog-profile-editing.md` for the detailed contract.

### Restaurant-discovery UX

Restaurant discovery now distinguishes local capability from a live provider request.

- disabled discovery prevents submission;
- missing Family restaurant area is explained and an explicit search area can still be entered;
- a provider outage no longer surfaces only a raw `HTTP 503` message;
- the Family settings page exposes the integration state for Restaurants and delivery providers.

A capability marked configured does not guarantee that an external OpenStreetMap/Nominatim/Overpass request will respond at that instant.

### UI cleanup

This branch also includes:

- responsive Family and Person edit forms;
- timezone selectors based on browser-supported IANA zones;
- clearer shared/read-only Ingredient states;
- Recipe nutrition evidence badges and filters;
- Ingredient nutrition status/usage indicators and filters;
- preference rating layout fixes so stars/actions do not overflow their cards;
- friendlier Restaurant provider-state/error presentation.

## Validation state

Do not treat this branch as green until the exact final head has passed the relevant gates.

Push-triggered GitHub Actions are not currently visible through the connected legacy status endpoint used during this work; an empty status list is **not** evidence of green CI.

Required local gates on the exact final head:

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

After local green confirmation, verify API CI and Web CI on the exact GitHub head before integration.

## Smoke-test focus for this branch

After both CIs are green on the exact final head:

1. edit Family name/timezone/restaurant area and verify the shell refreshes;
2. edit only a Person name and verify the profile/list refresh without an energy regression;
3. edit Person weight/activity and verify energy/profile values refresh;
4. confirm v1/shared Ingredients are visible, read-only and show Recipe usage counts;
5. test Ingredient nutrition filters;
6. open a legacy-v1 Recipe and verify its calories are labelled as a development estimate;
7. verify exact Ingredient blockers on an incomplete Recipe;
8. create a Family Ingredient with energy, use it in a Family Recipe and confirm automatic Recipe calorie calculation;
9. test Recipe nutrition-quality filters;
10. verify Restaurant capability messaging and friendly external-provider failure handling.

Use the existing development database. Do not delete its Docker volume.

## Deferred / next work

The immediate follow-up after this branch should be trustworthy catalogue enrichment rather than adding more synthetic calories. Candidate scope:

```text
authoritative generic-food nutrition source
+ explicit Ingredient matching/review
+ source/version provenance
+ unit/reference normalization
+ Recipe recalculation from enriched Ingredients
+ clear distinction between curated, user-entered and demo nutrition
```

Broader limitations remain:

- Family UUID is still development context, not production authorization;
- production authentication/Family authorization is not implemented;
- purchased ShoppingListItem does not automatically create PantryStockLot;
- npm lockfile / npm ci production hardening remains pending;
- external commercial meal integrations still depend on provider access/configuration.

## Resume procedure

1. read this file, ADR-007 and relevant domain docs;
2. inspect exact `main`, active branch and schema head;
3. confirm local gate result on the exact branch head;
4. never PR/merge an unvalidated head;
5. after merge verify exact new `main` before starting the next block.
