# NutriFlow AI v2 development continuity

This is the authoritative handover entry point for NutriFlow AI v2. Repository code, migrations, tests, domain docs and ADRs take precedence over conversation history.

## Repository checkpoint

This handover rebaseline started from the following integrated code baseline:

```text
pre-rebaseline main SHA: cbb09ad1d5e079e6b73ada2ebcc25999b80eca9c
schema head:             a8f2c6d4e1b9
```

PR #36 closes the documentation rebaseline and the CI dependency-resolution issue discovered while validating it. Its exact tested head is:

```text
PR #36 tested head: 0043a5782e2a3e929cdbecc53e317a2820bbc7f3
API CI:             success
Web CI:             success
```

The schema is unchanged by this checkpoint. The API test environment now caps the development/test AnyIO dependency below 4.15 because Starlette 1.6.0's released TestClient still imports a deprecated AnyIO alias and this project intentionally treats warnings as errors. Remove that cap only after validating an upstream Starlette release that contains the TestClient fix.

Do **not** treat either SHA above as the forever-current `main`. At every new session, resolve `refs/heads/main` first and verify open PRs/CI before creating new work.

There is no product feature work intentionally left open at this checkpoint. Historical feature branches remain in the repository, but they must not be treated as active work merely because their refs still exist. `feature/family-catalog-and-profile-editing` is an ancestor of the pre-rebaseline `main` and its work is already integrated.

Do not resume from an old feature branch. New work starts from the exact current `main` after reconfirming the ref.

## Product direction

NutriFlow AI v2 is a standalone, person-centric adaptive nutrition platform for individuals and families.

The implemented operational chain now covers:

```text
Family / Persons
-> profiles, goals, targets and constraints
-> Ingredients and versioned food composition
-> Recipes and calculated/versioned recipe nutrition
-> Family meal planning
-> Person-specific portions / Servings
-> Pantry
-> Shopping
-> preferences / ratings / feedback
-> recommendation refinement and diversity
-> restaurant / delivery availability and external menu ingestion
```

The next product step is to add a first-class **Nutrition Plan / Guidance** layer that turns nutritionist-, clinician- or user-defined plans into structured rules that can evaluate, transform and recommend meals across home cooking, existing recipes, restaurant food and delivery.

The detailed roadmap is authoritative in:

`docs/vision/nutrition-plan-guidance-roadmap.md`

## Core invariants

Preserve all of the following:

- Person remains the primary nutrition entity inside Family context;
- one shared MealEvent can have multiple MealParticipants;
- each participant has Person-specific Servings;
- normal meal planning uses exactly `breakfast`, `lunch`, `snack` and `dinner`;
- Food/Recipe composition is versioned and historical provenance is preserved;
- anthropometric history is append-only when a measurement actually changes;
- hard adverse-reaction and mandatory nutrition rules run before preference, ranking or ML signals;
- missing nutrition evidence is unknown, never silently zero;
- unsafe unit conversions are rejected rather than guessed;
- browser code presents server-authoritative nutrition, planning, shopping and ranking evidence;
- user preference is separate from algorithmic nutrition/practical score;
- professional guidance must retain source/provenance and must not be silently overridden;
- shared catalogue entities are visible to Families but remain read-only unless explicitly owned by that Family;
- demo or synthetic evidence must remain explicitly identified and must never be presented as equivalent to curated/measured nutrition;
- persisted timezone values must be valid IANA timezone names.

## Implemented foundation

### Person and Family

Implemented:

- Family and Person domain;
- editable Family settings including timezone and meal-discovery context;
- Person identity/profile editing;
- anthropometric history;
- activity/energy profile inputs;
- NutritionGoal history;
- versioned NutritionTarget snapshots;
- NutritionConstraint with provenance, severity and mandatory/advisory semantics;
- FoodPreference and adverse-reaction records;
- ScheduleEntry context;
- health-provider connection and normalized health-measurement foundations;
- DailyHealthState and DailyNutritionState snapshots.

### Food, recipes and household operations

Implemented:

- Family-owned and shared FoodItem catalogue;
- versioned FoodCompositionSnapshot and nutrient components;
- ingredient quality/provenance visibility;
- Recipe and ordered RecipeIngredient editing;
- deterministic recipe nutrition calculation;
- versioned RecipeCompositionSnapshot provenance;
- fail-closed incomplete/unsafe nutrition evidence;
- pantry stock with quantity, location and expiry;
- planned ingredient requirements;
- durable ShoppingList / ShoppingListItem flow.

### Meal planning and recommendations

Implemented:

- Family Today/Week planner;
- shared MealEvent plus Person-specific Serving quantities;
- planned-meal replacement/idempotency semantics;
- deterministic DailyNutritionState recalculation;
- hard-rule-first recommendation ranking;
- nutrition fit, preference and practical-context scoring;
- shared-family recommendation with per-Person safety evaluation;
- Person/Recipe ratings and Family aggregate preference;
- history/diversity signals and repeat penalties;
- category/protein rotation and meal-type suitability;
- persisted recommendation runs/options/feedback;
- accepted/modified recommendations materialized into normal meal records.

### Restaurant and delivery foundation

Implemented abstractions already support:

```text
home
pantry
restaurant
delivery
store
```

The platform has persisted source availability, opening windows, commercial offers and external-menu ingestion. External dishes can become normal FoodItems with composition snapshots, availability and offers, allowing the same recommendation engine to score them when nutrition evidence is sufficient.

Provider access remains a separate concern. Uber Eats consumer discovery requires approved access; public Glovo/Bolt Food interfaces do not currently provide a general consumer marketplace discovery contract. Product logic must therefore remain provider-agnostic and must not depend on one delivery API.

## Frontend information architecture

Keep the current family-first progressive-disclosure approach. Primary navigation remains conceptually:

```text
Início
Refeições
Pessoas
Casa
Mais
```

Use focused screens rather than dense dashboards.

Current important areas include:

```text
Refeições -> Hoje | Semana | Recomendar
Casa      -> Receitas | Ingredientes | Despensa | Compras | Preferências
Pessoas   -> Visão geral | Nutrição | Atividade | Saúde | Histórico | Perfil
```

The future Nutrition Plan UI belongs under the selected Person, not as a new top-level Family menu. Keep **nutrition plan** distinct from **meal plan**:

```text
Pessoas -> <Person> -> Nutrição -> Plano
Refeições -> Hoje / Semana / Recomendar
```

## Closed work / no longer active

The following lines of work are considered integrated/closed for planning purposes:

- core meal-planning foundation;
- Family-first Home and Person drill-down;
- preferences and diverse recommendation ranking;
- family catalogue/profile editing;
- automatic meal-intelligence refinements present in current `main`;
- future-planning demo-test stabilization;
- CI dependency-resolution stabilization recorded in PR #36.

Do not reopen these as standalone roadmap items unless a concrete regression or new requirement appears.

## Next development programme

The next coherent programme is **Nutrition Plan & Guidance**.

Sequence:

```text
0. Reconfirm current main / schema / CI baseline
1. NutritionPlan domain and provenance
2. EffectiveNutritionPlan compiler per Person/date/meal/context
3. Plan import/parser with explicit user confirmation
4. Meal Plan-Fit evaluation and explanations
5. Structured Meal Transformation proposals
6. Home/pantry/recipe recommendations using Plan-Fit
7. Restaurant/delivery recommendations using the same Plan-Fit
8. Weekly adaptive planning using plan rules + diversity + household constraints
9. Feedback/learning refinement
```

A parallel enabling track is trustworthy catalogue enrichment. Meal evaluation and transformation should not pretend precision where composition evidence is missing or synthetic.

Do not build separate scoring engines for recipes, Uber Eats, Glovo or restaurants. All meal candidates should converge on the existing FoodItem/Recipe composition and recommendation abstractions.

## Immediate next branch

Recommended next branch name:

```text
feature/nutrition-plan-guidance-foundation
```

Its first scope should stop after the domain and compiler are sound. Do not start with the frontend parser or delivery integration.

Minimum first-block deliverables:

- `NutritionPlan` identity/version/source/lifecycle model;
- explicit association of plan-owned rules/targets/guidelines;
- distinction between professional prescription, user input and NutriFlow-derived guidance;
- meal-context rules, including per-meal nutrient targets;
- weekly-frequency/qualitative guideline representation without forcing every guideline into `NutritionConstraint`;
- deterministic `EffectiveNutritionPlan` service;
- tests covering provenance, priority, date validity, mandatory rules and meal context;
- migration and domain/ADR documentation;
- no silent conversion of free text into active mandatory rules.

See `docs/vision/nutrition-plan-guidance-roadmap.md` before implementation.

## Known broader limitations

- production authentication and Family authorization are not implemented;
- Family UUID is still development context;
- purchased ShoppingListItem does not automatically create PantryStockLot;
- external commercial meal discovery depends on provider access/configuration;
- nutrition evidence quality varies by catalogue item and must remain visible;
- professional-plan document ingestion/parser is not yet implemented;
- meal transformation is not yet implemented;
- npm lockfile / `npm ci` production hardening remains pending.

## Delivery workflow

Authoritative workflow decision: `docs/decisions/ADR-007-development-workflow-and-ci.md`.

For each functional block:

1. resolve the exact `main` SHA;
2. create a focused branch from that SHA;
3. build code, migration, tests and docs together;
4. run all relevant local gates on the exact final head;
5. warnings are failures;
6. open a PR only after local green confirmation;
7. verify GitHub Actions on the exact PR head;
8. verify mergeability and unchanged head;
9. guarded squash merge using the expected head SHA;
10. verify resulting `main` before starting the next block.

Never use `docker compose down -v` as a routine smoke-test reset because the development PostgreSQL volume may contain user-created data.

## Resume procedure

At the start of the next development session:

1. read this file;
2. read `docs/vision/nutrition-plan-guidance-roadmap.md`;
3. inspect the exact current `main` ref and open PRs;
4. run/confirm the current migration and validation baseline;
5. create `feature/nutrition-plan-guidance-foundation` from verified `main`;
6. implement Phase 1 domain/compiler only before moving to parser, transformations or delivery UX.
