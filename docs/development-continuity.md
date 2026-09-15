# NutriFlow AI v2 development continuity

This is the authoritative handover entry point for NutriFlow AI v2. Repository code, migrations, tests, domain docs and ADRs take precedence over conversation history.

## Repository checkpoint

Nutrition Plan / Guidance has progressed through the plan foundation and the reviewed text-import boundary.

```text
PR #37 base main:      9d82a148992a788d484e28d21f595724530ae9d5
PR #37 merged main:    ff53a7b6f3dbb9d9acfbab6ef544ff61b7c71faa
PR #38 code checkpoint:b283164bcd16bdcffacb47a32e0ca7e7138aa84c
schema progression:    a8f2c6d4e1b9 -> b9e3f7c1d4a6 -> c1f4a8d2e6b9
```

The PR #38 code checkpoint above passed API and Web CI on the exact head, including PostgreSQL migrations, `alembic check`, Ruff and the complete API test suite. Documentation commits may move the final PR head; validate the exact final head again before merge.

Do **not** treat any SHA in this document as permanently current. At every new session resolve `refs/heads/main`, inspect open PRs and confirm CI before creating new work.

The API test environment currently caps the development/test AnyIO dependency below 4.15 because Starlette 1.6.0's released TestClient still imports a deprecated AnyIO alias and this project intentionally treats warnings as errors. Remove that cap only after validating an upstream Starlette release containing the TestClient fix.

Historical feature branches may remain in the repository. A branch ref is not evidence of unfinished work; open PRs plus this handover define active work.

## Product direction

NutriFlow AI v2 is a standalone, person-centric adaptive nutrition platform for individuals and families.

The implemented operational chain now covers:

```text
Family / Persons
-> profiles, goals, targets and constraints
-> versioned Nutrition Plans and meal-context guidance
-> pasted plan text -> reviewable structured proposals -> confirmed draft plan content
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

The next product capability is **Meal Plan-Fit**: evaluate any normalized meal candidate against the server-authoritative `EffectiveNutritionPlan`, surface hard-rule failures, strengths, gaps and missing evidence, and provide one common contract for later recipe transformation and recommendation ranking.

Authoritative roadmap:

`docs/vision/nutrition-plan-guidance-roadmap.md`

Core domain documents:

- `docs/domain/nutrition-plan-model.md`
- `docs/domain/nutrition-plan-import-review.md`

Decision records:

- `docs/decisions/ADR-035-nutrition-plan-guidance-foundation.md`
- `docs/decisions/ADR-036-nutrition-plan-import-review-boundary.md`

## Core invariants

Preserve all of the following:

- Person remains the primary nutrition entity inside Family context;
- one shared MealEvent can have multiple MealParticipants;
- each participant has Person-specific Servings;
- normal meal planning uses exactly `breakfast`, `lunch`, `snack` and `dinner`;
- Nutrition Plan is distinct from Meal Plan;
- active professional-plan content is immutable; substantive changes create a new version;
- plan source/provenance and original statements remain traceable;
- parser/AI interpretations never silently become active professional rules;
- every imported proposal must be explicitly confirmed or rejected before materialization;
- applying an import materializes confirmed content into a draft plan and does not activate it;
- Food/Recipe composition is versioned and historical provenance is preserved;
- anthropometric history is append-only when a measurement actually changes;
- hard adverse-reaction and mandatory nutrition rules run before preference, ranking or ML signals;
- missing nutrition evidence is unknown, never silently zero;
- unsafe unit conversions are rejected rather than guessed;
- browser code presents server-authoritative nutrition, planning, shopping and ranking evidence;
- user preference is separate from algorithmic nutrition/practical score;
- professional guidance is not silently overridden by lower-authority guidance;
- conflicts are surfaced rather than silently resolved;
- shared catalogue entities are visible to Families but remain read-only unless explicitly owned by that Family;
- demo or synthetic evidence remains explicitly identified and is never presented as equivalent to curated/measured nutrition;
- persisted timezone values are valid IANA timezone names.

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

### Nutrition Plan / Guidance foundation — PR #37

Implemented:

- Person-scoped `NutritionPlan` with lineage/version/supersession semantics;
- lifecycle states `draft`, `active`, `inactive`, `superseded`;
- nutritionist, clinician, user, system and imported source categories;
- source name/reference and original plan text retention;
- date validity and draft-only content mutation;
- active-plan immutability and version cloning;
- activation that supersedes the prior active lineage version while preserving historical applicability;
- typed `NutritionPlanRule` bindings to existing `NutritionConstraint`, `NutritionTargetComponent` and `NutritionGoal`;
- meal-type scope, local priority, validity and original source statements on rule bindings;
- plan-only vs independently applicable rule semantics;
- `NutritionPlanGuideline` for qualitative and weekly-frequency guidance;
- proposed/confirmed/rejected guideline state;
- deterministic `EffectiveNutritionPlan` compiler for Person + date + meal type;
- mandatory-before-advisory deterministic ordering with provenance retained;
- explicit numeric min/max conflict reporting;
- plan-bound target/goal snapshot semantics across later energy-profile recalculation;
- Person-scoped CRUD/version/rule/guideline API and effective-plan endpoint;
- schema revision `b9e3f7c1d4a6`.

### Nutrition Plan import / review — PR #38

Implemented:

- `NutritionPlanImportSession` linked to one new draft NutritionPlan;
- `NutritionPlanImportProposal` staging records with verbatim source statement, normalized fields, parser confidence/note and review notes;
- proposal states `proposed`, `confirmed`, `rejected`;
- proposal types `numeric_rule`, `qualitative_guideline`, `frequency_guideline`, `unclassified`;
- deterministic conservative PT/EN parser v1 for common nutrient numbers/ranges, meal scope, weekly food-category frequencies and qualitative directives;
- unknown/ambiguous statements preserved as `unclassified` rather than guessed or discarded;
- manual proposal editing/addition during review;
- atomic candidate-state validation before proposal mutation;
- explicit requirement that every proposal be confirmed or rejected before apply;
- confirmed `unclassified` proposal blocks apply until edited or rejected;
- confirmed numeric proposals materialize as `NutritionConstraint + NutritionPlanRule`;
- confirmed qualitative/frequency proposals materialize as confirmed `NutritionPlanGuideline`;
- source type/name/reference and source statements remain traceable into materialized content;
- imported plan remains draft after apply; activation is a separate NutritionPlan lifecycle action;
- plan-bound imported constraints use `applies_outside_plan=False`, so the EffectiveNutritionPlan compiler does not duplicate them as standalone constraints;
- Person-scoped import list/create/read, proposal add/update, apply and cancel endpoints;
- service/API tests covering parse -> review -> apply -> activate -> EffectiveNutritionPlan and invalid-edit atomicity;
- ADR-036 and domain documentation;
- schema revision `c1f4a8d2e6b9`.

Not yet implemented:

- PDF/photo/document extraction adapters;
- LLM-assisted parser adapter;
- focused frontend review screen under Person -> Nutrição -> Plano;
- weekly frequency-progress calculation;
- Meal Plan-Fit candidate evaluation;
- Meal Transformation.

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
- existing nutrition-fit, preference and practical-context scoring;
- shared-family recommendation with per-Person safety evaluation;
- Person/Recipe ratings and Family aggregate preference;
- history/diversity signals and repeat penalties;
- category/protein rotation and meal-type suitability;
- persisted recommendation runs/options/feedback;
- accepted/modified recommendations materialized into normal meal records.

The Phase 4 Plan-Fit work must reuse useful existing recommendation nutrition logic rather than create an unrelated second score. The new contract must add EffectiveNutritionPlan-aware evidence/explanations and become the common downstream evaluator.

### Restaurant and delivery foundation

Implemented abstractions support:

```text
home
pantry
restaurant
delivery
store
```

The platform has persisted source availability, opening windows, commercial offers and external-menu ingestion. External dishes can become normal FoodItems with composition snapshots, availability and offers, allowing the same future Plan-Fit evaluator to handle them when evidence is sufficient.

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
3. Plan import/parser with explicit confirmation                         DONE
4. Meal Plan-Fit evaluation and explanations                            NEXT
5. Structured Meal Transformation proposals                             PENDING
6. Home/pantry/recipe recommendations using Plan-Fit                     PENDING
7. Restaurant/delivery recommendations using the same Plan-Fit           PENDING
8. Weekly adaptive planning using plan rules + diversity + constraints   PENDING
9. Feedback/learning refinement                                          PENDING
```

Phase 2 can later gain richer daily-state/weekly-progress context without changing the deterministic compiler boundary already used downstream.

A parallel enabling track is trustworthy catalogue enrichment. Meal evaluation and transformation must not pretend precision where composition evidence is missing or synthetic.

## Immediate next block

Recommended next branch:

```text
feature/nutrition-plan-fit-evaluation
```

Scope only **Meal Plan-Fit evaluation and explanations**, not transformation yet.

Minimum next-block deliverables:

- inspect and reuse the current recommendation nutrition-fit/hard-rule logic where semantics match;
- define one server-authoritative `MealPlanFit` contract for a Person/date/meal/candidate;
- normalize candidate nutrition evidence from existing Recipe/FoodItem composition snapshots instead of source-specific evaluators;
- evaluate mandatory rules first and keep hard failure separate from any weighted score;
- compare known nutrient evidence against EffectiveNutritionPlan numeric rules/targets;
- surface matched strengths, gaps, conflicts and missing evidence;
- preserve source/provenance in explanations;
- never treat missing nutrient evidence as zero;
- keep qualitative/frequency guidance explicit where evidence is insufficient rather than pretending it was measured;
- provide API/service tests proving the same evaluator works for at least Recipe and FoodItem candidates;
- document how the existing recommendation engine will consume Plan-Fit later without duplicating scoring logic.

Do not start Meal Transformation or provider-specific integrations in this block.

## Known broader limitations

- production authentication and Family authorization are not implemented;
- Family UUID is still development context;
- purchased ShoppingListItem does not automatically create PantryStockLot;
- external commercial meal discovery depends on provider access/configuration;
- nutrition evidence quality varies by catalogue item and remains visible;
- PDF/photo/document and LLM plan ingestion adapters are not yet implemented;
- frontend plan import/review UI is not yet implemented;
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
4. run all relevant local gates on the exact final head when a local environment is available;
5. warnings are failures;
6. open a PR and verify GitHub Actions on the exact PR head;
7. never rely on checks from an earlier head;
8. verify mergeability and unchanged head;
9. guarded squash merge using the expected head SHA;
10. verify resulting `main` before starting the next block.

Never use `docker compose down -v` as a routine smoke-test reset because the development PostgreSQL volume may contain user-created data.

## Resume procedure

At the start of the next development session:

1. read this file;
2. read `docs/vision/nutrition-plan-guidance-roadmap.md`;
3. read the Nutrition Plan model/import domain docs and ADR-035/ADR-036;
4. inspect the exact current `main` ref and open PRs;
5. confirm schema head and validation baseline;
6. create `feature/nutrition-plan-fit-evaluation` from verified `main`;
7. inspect existing recommendation nutrition-fit/hard-rule services before designing the common Meal Plan-Fit contract;
8. implement Plan-Fit before Meal Transformation, delivery-specific logic or broad frontend work.
