# Domain implementation status

`docs/development-continuity.md` is the handover entry point. This file summarizes the current domain baseline and the next planned capability.

## Current Nutrition Plan chain

```text
NutritionPlan domain/provenance                    IMPLEMENTED
EffectiveNutritionPlan compiler                   FOUNDATION IMPLEMENTED
Plan text import + explicit review/confirmation   IMPLEMENTED
MealPlanFit candidate evaluation                  IMPLEMENTED v1
Structured Meal Transformation                    NEXT
```

Current schema head remains:

```text
c1f4a8d2e6b9
```

MealPlanFit is calculation-only in v1, so Phase 4 adds no database migration.

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
- explicit proposed/confirmed/rejected review gate;
- `unclassified` ambiguity preservation;
- confirmed proposal materialization into draft plan content;
- separate explicit activation after import apply.

Deferred plan ingestion:

- PDF/photo/document extraction;
- LLM-assisted parser adapter;
- focused browser import/review UI.

## Meal Plan-Fit v1

Implemented in PR #39:

- one server-authoritative evaluator for FoodItem and Recipe candidates;
- input reuses recommendation candidate identity: composition snapshot + quantity/unit;
- existing versioned composition scaling and safe unit conversion are reused;
- EffectiveNutritionPlan is the rule source;
- meal-scoped numeric guidance is compared directly with candidate evidence;
- candidate-level exclusions are evaluated from normalized candidate subjects;
- global nutrient guidance is treated as daily context rather than a per-meal target;
- DailyNutritionState can be supplied explicitly or auto-selected for Person/date;
- projected daily totals include existing state plus candidate contribution;
- daily minimum/range rules can return `support` when a meal improves progress without completing the day;
- mandatory daily rules with missing context/evidence fail closed as `unknown`;
- mandatory adverse reactions remain independent hard gates;
- mandatory plan conflicts block eligibility;
- overall status is independent from numeric score;
- fit score is 0..1 over scored candidate/meal numeric rules only;
- qualitative/frequency guidance is returned visibly as `not_evaluated` rather than guessed;
- source/provenance is preserved in each result;
- no provider-specific scoring semantics.

API:

```text
POST /api/persons/{person_id}/meal-plan-fit
```

Web test surface:

```text
Pessoas -> <Person> -> Nutrição -> Adequação ao plano
```

The panel selects meal type, Recipe and portion and renders fit score, eligibility, active plans, rule results, projected daily totals, conflicts, safety blocks and unscored guidance.

Development seed provides an active breakfast plan for the technical demo Person:

```text
protein >= 15 g  mandatory
fiber   >= 6 g   advisory
prefer whole fruit  qualitative/unscored
```

The development breakfast catalogue provides contrasting recipes so a user can immediately compare a fitting and non-fitting candidate.

Decision record: `docs/decisions/ADR-037-meal-plan-fit-evaluation.md`.

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

Important next integration rule: recommendation ranking must progressively consume MealPlanFit instead of allowing its legacy nutrition-rule evaluation to evolve independently. Preference/practical/diversity scoring remains a distinct layer.

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
- professional provenance is retained;
- conflicts are surfaced;
- Family isolation and Person-specific portions;
- historical Serving evidence remains stable;
- demo evidence is explicitly synthetic/development-only;
- warnings are failures.

## Next development block

After PR #39 is merged and browser-tested, proceed to structured Meal Transformation.

Recommended branch:

```text
feature/meal-transformation-proposals
```

Target contract:

```text
candidate
-> baseline MealPlanFit
-> structured operations
   ADD / REMOVE / REDUCE / INCREASE / SWAP / CHANGE_COOKING_METHOD / CHANGE_PORTION
-> recalculated candidate evidence
-> resulting MealPlanFit
-> explain eligibility/score delta
```

Before or during that phase, factor recommendation nutrition-rule evaluation onto MealPlanFit so there is one nutrition-plan-aware evaluator rather than parallel scoring logic.

## Broader deferred limitations

- production authentication / Family authorization;
- shopping purchase -> pantry reconciliation;
- trustworthy catalogue coverage is incomplete;
- production consumer marketplace adapters depend on provider access;
- PDF/photo/document and LLM plan parser adapters;
- frontend plan import/review screen;
- weekly frequency-progress calculation;
- qualitative/frequency Plan-Fit scoring;
- recommendation engine not yet consuming MealPlanFit directly;
- Meal Transformation engine;
- npm lockfile / `npm ci` production hardening.
