# NutriFlow AI v2 development continuity

This is the authoritative handover entry point for NutriFlow AI v2. Repository code, migrations, tests, domain docs and ADRs take precedence over conversation history.

## Repository checkpoint

The Nutrition Plan / Guidance foundation was built from verified `main`:

```text
base main SHA: 9d82a148992a788d484e28d21f595724530ae9d5
previous schema head: a8f2c6d4e1b9
new schema head:      b9e3f7c1d4a6
PR:                   #37
```

Do **not** treat the SHA above as permanently current. At every new session resolve `refs/heads/main`, inspect open PRs and confirm CI before creating new work.

The API test environment currently caps the development/test AnyIO dependency below 4.15 because Starlette 1.6.0's released TestClient still imports a deprecated AnyIO alias and this project intentionally treats warnings as errors. Remove that cap only after validating an upstream Starlette release containing the TestClient fix.

Historical feature branches may remain in the repository. A branch ref is not evidence of unfinished work; open PRs plus this handover define active work.

## Product direction

NutriFlow AI v2 is a standalone, person-centric adaptive nutrition platform for individuals and families.

The implemented operational chain now covers:

```text
Family / Persons
-> profiles, goals, targets and constraints
-> versioned Nutrition Plans and meal-context guidance
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

The Nutrition Plan layer is now a first-class domain capability. The next step is to make external/professional plan text ingestible as **proposed structured guidance that must be explicitly reviewed/confirmed before activation**.

Authoritative roadmap:

`docs/vision/nutrition-plan-guidance-roadmap.md`

Domain detail:

`docs/domain/nutrition-plan-model.md`

Decision record:

`docs/decisions/ADR-035-nutrition-plan-guidance-foundation.md`

## Core invariants

Preserve all of the following:

- Person remains the primary nutrition entity inside Family context;
- one shared MealEvent can have multiple MealParticipants;
- each participant has Person-specific Servings;
- normal meal planning uses exactly `breakfast`, `lunch`, `snack` and `dinner`;
- Nutrition Plan is distinct from Meal Plan;
- active professional-plan content is immutable; substantive changes create a new version;
- plan source/provenance and original statements must remain traceable;
- AI/imported interpretations must never silently become active professional rules;
- Food/Recipe composition is versioned and historical provenance is preserved;
- anthropometric history is append-only when a measurement actually changes;
- hard adverse-reaction and mandatory nutrition rules run before preference, ranking or ML signals;
- missing nutrition evidence is unknown, never silently zero;
- unsafe unit conversions are rejected rather than guessed;
- browser code presents server-authoritative nutrition, planning, shopping and ranking evidence;
- user preference is separate from algorithmic nutrition/practical score;
- professional guidance must not be silently overridden by lower-authority guidance;
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

### Nutrition Plan / Guidance

Implemented in PR #37:

- Person-scoped `NutritionPlan` with `lineage_id`, positive version and `supersedes_plan_id`;
- lifecycle states `draft`, `active`, `inactive`, `superseded`;
- source categories for nutritionist, clinician, user, system and imported plans;
- source name/reference and original plan text retention;
- date validity;
- draft-only content editing;
- new-version cloning of rule bindings and guidelines;
- activation that supersedes the prior active version in the same lineage while preserving historical date applicability;
- typed `NutritionPlanRule` bindings to existing `NutritionConstraint`, `NutritionTargetComponent` and `NutritionGoal`;
- meal-type scope, local priority, narrower validity and original source statements on rule bindings;
- `NutritionPlanGuideline` for qualitative and weekly-frequency guidance;
- explicit proposed/confirmed/rejected guideline state;
- deterministic `EffectiveNutritionPlan` compiler for Person + date + meal type;
- professional/user/system source precedence used for deterministic ordering only;
- mandatory rules ordered above advisory rules without silently deleting lower-priority guidance;
- explicit numeric min/max conflict reporting;
- preservation of plan-bound target/goal snapshot semantics if a later energy-profile recalculation supersedes the global current target/goal;
- Person-scoped CRUD/version/rule/guideline API plus effective-plan read endpoint;
- schema head `b9e3f7c1d4a6`.

Not yet implemented:

- document/text parser;
- proposal-review confirmation UX;
- Meal Plan-Fit candidate evaluation;
- Meal Transformation;
- weekly frequency-progress calculation;
- frontend Nutrition Plan screens.

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

Implemented abstractions support:

```text
home
pantry
restaurant
delivery
store
```

The platform has persisted source availability, opening windows, commercial offers and external-menu ingestion. External dishes can become normal FoodItems with composition snapshots, availability and offers, allowing the same recommendation engine to score them when nutrition evidence is sufficient.

Provider access remains separate from NutriFlow domain logic. Do not build provider-specific nutrition/scoring engines.

## Frontend information architecture

Keep the family-first progressive-disclosure approach:

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

Nutrition Plan belongs under the selected Person and remains distinct from Meal Plan:

```text
Pessoas -> <Person> -> Nutrição -> Plano
Refeições -> Hoje / Semana / Recomendar
```

## Nutrition Plan & Guidance roadmap state

```text
0. Reconfirm current main / schema / CI baseline                         DONE
1. NutritionPlan domain and provenance                                  DONE
2. EffectiveNutritionPlan compiler per Person/date/meal context          FOUNDATION DONE
3. Plan import/parser with explicit user confirmation                    NEXT
4. Meal Plan-Fit evaluation and explanations                            PENDING
5. Structured Meal Transformation proposals                             PENDING
6. Home/pantry/recipe recommendations using Plan-Fit                     PENDING
7. Restaurant/delivery recommendations using the same Plan-Fit           PENDING
8. Weekly adaptive planning using plan rules + diversity + constraints   PENDING
9. Feedback/learning refinement                                          PENDING
```

Phase 2 will be extended later with richer daily-state/weekly-progress context, but the deterministic compiler contract required by downstream work now exists.

A parallel enabling track is trustworthy catalogue enrichment. Meal evaluation and transformation must not pretend precision where composition evidence is missing or synthetic.

## Immediate next block

Recommended next branch:

```text
feature/nutrition-plan-import-confirmation
```

Scope only **plan import/parser + explicit confirmation**, not Meal Plan-Fit yet.

Minimum next-block deliverables:

- ingestion request that preserves original source text/document reference;
- deterministic parser contract separated from model activation;
- parsed/proposed rule and guideline representation with confidence/evidence metadata;
- explicit mapping to existing NutritionConstraint / NutritionTarget / NutritionGoal semantics where appropriate;
- confirmation/rejection/edit workflow before any proposal becomes effective;
- no automatic activation from raw text or AI output;
- parser tests for numeric targets, meal-specific guidance, qualitative guidance, frequency guidance and ambiguous statements;
- API/domain docs and, only after backend semantics are stable, a focused Person -> Nutrição -> Plano review screen.

Do not start Meal Transformation, provider integration or a broad frontend redesign in this block.

## Known broader limitations

- production authentication and Family authorization are not implemented;
- Family UUID is still development context;
- purchased ShoppingListItem does not automatically create PantryStockLot;
- external commercial meal discovery depends on provider access/configuration;
- nutrition evidence quality varies by catalogue item and must remain visible;
- professional-plan document ingestion/parser is not yet implemented;
- weekly frequency progress is not yet evaluated;
- Meal Plan-Fit is not yet implemented;
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
6. open a PR only after local green confirmation when a local environment is available;
7. verify GitHub Actions on the exact PR head;
8. verify mergeability and unchanged head;
9. guarded squash merge using the expected head SHA;
10. verify resulting `main` before starting the next block.

Never use `docker compose down -v` as a routine smoke-test reset because the development PostgreSQL volume may contain user-created data.

## Resume procedure

At the start of the next development session:

1. read this file;
2. read `docs/vision/nutrition-plan-guidance-roadmap.md`;
3. read `docs/domain/nutrition-plan-model.md` and ADR-035;
4. inspect the exact current `main` ref and open PRs;
5. confirm schema head and validation baseline;
6. create `feature/nutrition-plan-import-confirmation` from verified `main`;
7. implement parser/proposal/confirmation semantics before Plan-Fit, transformations or delivery UX.
