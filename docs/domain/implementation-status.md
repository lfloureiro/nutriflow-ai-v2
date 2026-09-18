# Domain implementation status

`docs/development-continuity.md` is the handover entry point. This file summarizes the current domain baseline and the next planned capability.

## Current Nutrition Plan chain

```text
NutritionPlan domain/provenance                    IMPLEMENTED
EffectiveNutritionPlan compiler                   FOUNDATION IMPLEMENTED
Plan text import + explicit review/confirmation   IMPLEMENTED
AI-assisted text interpretation + review UI       IMPLEMENTED v1
MealPlanFit candidate evaluation                  IMPLEMENTED v1
Structured Meal Transformation                    IMPLEMENTED v1 proposal slice
Plan-Fit-aware recommendation integration         NEXT
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
- mandatory machine-evaluable nutrient rules with missing context/evidence fail closed as `unknown`;
- mandatory guidance outside the current meal-evaluable scope (for example lifestyle, supplement, timing or unsupported qualitative directives) remains visible as partial coverage instead of becoming a universal meal veto;
- mandatory weekly maxima still fail closed when safe remaining capacity cannot be established from structured evidence; weekly minima remain support signals rather than per-meal gates;
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

- persistent Recipe-variant materialization after explicit acceptance;
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

After the Structured Meal Transformation proposal slice is merged and browser-tested, integrate home/pantry/Recipe recommendation nutrition evaluation with MealPlanFit.

The target separation is:

```text
MealPlanFit
= nutrition-plan eligibility + nutrition fit + explanations

Recommendation ranking
= MealPlanFit result
+ practical availability
+ preference
+ diversity/history
```

Do not create a second nutrition-plan scorer in recommendation ranking.

## Broader deferred limitations

- production authentication / Family authorization;
- shopping purchase -> pantry reconciliation;
- trustworthy catalogue coverage is incomplete;
- production consumer marketplace adapters depend on provider access;
- PDF/photo/document plan extraction;
- weekly frequency-progress calculation;
- qualitative/frequency Plan-Fit scoring;
- recommendation engine not yet consuming MealPlanFit directly;
- transformation variant materialization and multi-operation optimization;
- npm lockfile / `npm ci` production hardening.
