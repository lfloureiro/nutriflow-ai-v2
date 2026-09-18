# Domain implementation status

`docs/development-continuity.md` is the handover entry point. This file summarizes the current domain baseline and the next planned capability.

## Current Nutrition Plan chain

```text
NutritionPlan domain/provenance                    IMPLEMENTED
EffectiveNutritionPlan compiler                   FOUNDATION IMPLEMENTED
Plan text/document import + review/confirmation   IMPLEMENTED v1
AI-assisted text interpretation + review UI       IMPLEMENTED v1
MealPlanFit candidate evaluation                  IMPLEMENTED v1
Structured Meal Transformation                    IMPLEMENTED v1
Plan-Fit-aware recommendation integration         IMPLEMENTED v1
Shared-Family transformation + materialization    IMPLEMENTED v1
Adaptive weekly planning                          IMPLEMENTED v1
Weekly plan -> shopping coupling                   IN PROGRESS
```

Feature schema head for Structured Meal Transformation:

```text
d2e6f1a9c4b7
```

It adds Family-scoped `FoodTransformationProfile` metadata. Meal transformation proposals themselves remain calculation-only.

## Person, Family and health context

Implemented:

- Family and Person;
- editable Person profile and energy inputs;
- anthropometric history;
- NutritionGoal history;
- versioned NutritionTarget components;
- NutritionConstraint with provenance/severity/mandatory semantics;
- FoodPreference and adverse-reaction evidence;
- ScheduleEntry context;
- HealthConnection / HealthMeasurement foundations;
- DailyHealthState and DailyNutritionState snapshots.

## Nutrition Plan / Guidance

Implemented:

- versioned Person-scoped NutritionPlan lineage and lifecycle;
- source/provenance and original source text/reference;
- draft-only editing and immutable active plan content;
- NutritionPlanRule bindings to constraints, target components and goals;
- meal scope, priority, date validity and source statement;
- NutritionPlanGuideline for qualitative/frequency guidance;
- deterministic EffectiveNutritionPlan compilation for Person/date/meal type;
- source/mandatory ordering without silent rule deletion;
- numeric conflict reporting;
- reviewed text import through NutritionPlanImportSession/Proposal;
- conservative PT/EN deterministic parser v1;
- optional AI-assisted interpretation using structured output;
- explicit proposed/confirmed/rejected review gate for deterministic and AI interpretation;
- `unclassified` ambiguity preservation;
- browser import/review surface under Person Nutrition;
- confirmed proposal materialization into draft plan content;
- separate explicit activation after import apply.

Deferred plan ingestion:

- PDF/photo/document extraction into the existing text-review boundary.

## Meal Plan-Fit v1

Implemented in PR #39:

- one server-authoritative evaluator for FoodItem and Recipe candidates;
- versioned composition scaling and safe unit conversion;
- EffectiveNutritionPlan as the rule source;
- meal-scoped numeric guidance compared directly with candidate evidence;
- candidate-level exclusions from normalized subjects;
- global nutrient guidance treated as daily context rather than a per-meal target;
- DailyNutritionState supplied explicitly or auto-selected for Person/date;
- projected daily totals include existing state plus candidate contribution;
- daily minimum/range rules can return `support`;
- mandatory daily rules with missing context/evidence fail closed as `unknown`;
- mandatory adverse reactions remain independent hard gates;
- mandatory plan conflicts block eligibility;
- overall status is independent from numeric score;
- fit score is 0..1 over scored candidate/meal numeric rules only;
- qualitative/frequency guidance remains visible as `not_evaluated`;
- provenance is preserved in each result;
- no provider-specific scoring semantics.

API:

```text
POST /api/persons/{person_id}/meal-plan-fit
```

Web surface:

```text
Pessoas -> <Person> -> Nutrição -> Adequação ao plano
```

## Structured Meal Transformation v1

Implemented in Phase 5 proposal slice:

- Family-scoped `FoodTransformationProfile` with explicit `substitution_group`;
- optional typical portion quantity/unit for explicit substitution equivalence;
- source/source-reference provenance and an enable flag;
- deterministic single-ingredient `replace_ingredient` operation;
- source Recipe remains immutable;
- baseline and transformed candidates use the same Meal Plan-Fit evaluator semantics;
- transformed nutrition is calculated virtually from composition evidence;
- unsafe conversions and incomplete evidence are skipped and exposed as limitations;
- only demonstrably improving replacements are returned;
- resolving a mandatory eligibility block is ranked above score-only improvement;
- daily-rule progress can qualify as an improvement without misreading daily targets as meal targets;
- proposal response contains before/after Plan-Fit, score delta, changed rule IDs and hard-block resolution;
- compact browser control appears only after evaluating a Recipe and exposes `Sugerir melhoria`.

API:

```text
POST /api/persons/{person_id}/meal-transformations/proposals
```

Development example:

```text
Iogurte, muesli e banana
baseline ~= 96.67%, blocked by breakfast protein >= 15 g

Iogurte natural 170 g -> Iogurte grego 170 g
result = 100%, eligible
```

The yogurt composition evidence used for this example is explicitly synthetic development data.

Decision/domain docs:

- `docs/decisions/ADR-039-structured-meal-transformation-proposals.md`
- `docs/domain/meal-transformation.md`

Deferred transformation work:

- persistent reusable Recipe-variant authoring after explicit acceptance;
- multiple simultaneous ingredient operations;
- add/remove/increase/reduce and cooking-method operations;
- pantry/cost/preparation optimization;
- AI/learned substitution generation without structured evidence.

## Catalogue and recipe evidence

Implemented:

- Family/shared FoodItem catalogue;
- versioned FoodCompositionSnapshot and nutrients;
- Recipe / RecipeIngredient;
- deterministic recipe composition calculation;
- versioned RecipeCompositionSnapshot;
- explicit nutrition provenance/readiness;
- safe conversions only; missing evidence remains unknown.

## Meals and household operations

Implemented:

- MealEvent + MealParticipant + Person-specific Serving;
- fixed meal types breakfast/lunch/snack/dinner;
- Today/Week family planner;
- planned-meal replacement/idempotency;
- immutable historical serving nutrition evidence;
- deterministic DailyNutritionState recalculation;
- pantry stock and expiry;
- aggregate planned ingredient requirements;
- durable shopping lists/items.

## Recommendation foundation

Implemented:

- hard-rule-first recommendation ranking;
- fail-closed mandatory evidence handling;
- legacy nutrition-fit score;
- preferences and Family aggregate preference;
- practical schedule/location/preparation context;
- shared-family recommendation with per-Person safety;
- persisted runs/options/feedback/decisions;
- diversity/history/repeat penalties;
- meal suitability and calorie-aware refinements.

Next integration rule: recommendation ranking must consume MealPlanFit for nutrition-plan-aware eligibility/fit instead of allowing its legacy nutrition-rule evaluation to evolve independently. Preference, practical context and diversity remain separate ranking layers.

## Adaptive weekly planning v1

Implemented:

- deterministic Person-specific weekly frequency progress;
- weekly-aware Meal Plan-Fit support/minimum and mandatory-maximum semantics;
- Person-specific weekly support in shared-Family ranking;
- full-week multi-slot optimization with same-day mandatory nutrient coupling;
- shared-Family weekly optimization using each Person's own Meal Plan-Fit evidence;
- server-authoritative weekly proposal orchestration;
- deterministic bounded search for larger candidate spaces;
- safe transformed Recipe variants participating directly in weekly optimization;
- atomic weekly materialization with stale-selection and slot-conflict protection;
- Monday-Sunday Week view with progressive disclosure and local rejection/recalculation;
- persisted transformation provenance visible after the weekly plan is applied;
- server-authoritative unavailable slots remain explicit pending gaps instead of invalidating the rest of an otherwise feasible week.

Current coupling increment:

- after successful weekly materialization, refresh the existing pantry-aware durable shopping list for the same Monday-Sunday interval;
- calculate transformed meals from persisted replacement ingredient provenance rather than the source Recipe ingredient;
- keep shopping refresh derivative: failure is surfaced separately and does not make an already-saved week appear rolled back.

## Restaurant and delivery foundation

Implemented abstractions:

- `MealCandidateAvailability` for home, pantry, restaurant, delivery and store;
- opening windows;
- commercial offers with provider/price/fees/minimum order/validity;
- external-menu normalization into FoodItem + optional composition + availability/offer.

Future restaurant/delivery Plan-Fit must use the same normalized evaluator. Provider access/configuration remains outside nutrition scoring.

## Safety and correctness invariants

Preserve:

- adverse reactions and mandatory constraints before ranking/ML;
- active professional-plan immutability;
- explicit parser review before imported content becomes plan content;
- separate explicit activation after import;
- missing evidence is unknown, not zero;
- unsafe conversion is rejected;
- mandatory missing evidence/context fails closed when needed;
- high fit score cannot override a hard failure or conflict;
- daily targets are not naively treated as per-meal targets;
- transformation proposals never silently mutate source Recipes;
- transformation equivalence requires explicit metadata/evidence rather than name inference;
- professional provenance is retained;
- conflicts are surfaced;
- Family isolation and Person-specific portions;
- historical Serving evidence remains stable;
- demo evidence is explicitly synthetic/development-only;
- warnings are failures.

## Next development block

Current branch: weekly plan -> shopping-list coupling.

After this slice is reviewed and eventually merged, the next Phase 8 work should remain focused on one product-visible capability at a time. Candidate increments are richer across-week category/protein diversity, explicit leftover/reservation evidence, or deeper pantry/schedule coupling. Do not start the next branch until this slice has been reviewed and merged explicitly.

## Broader deferred limitations

- production authentication / Family authorization;
- shopping purchase -> pantry reconciliation;
- trustworthy catalogue coverage is incomplete;
- production consumer marketplace adapters depend on provider access;
- OCR/photo/scanned-document extraction;
- qualitative guidance remains only partially machine-evaluable;
- transformation reusable-variant authoring and multi-operation optimization;
- explicit leftover/reservation inventory evidence;
- richer across-week category/protein diversity;
- npm lockfile / `npm ci` production hardening.
