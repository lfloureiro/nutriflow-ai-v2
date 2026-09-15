# Domain implementation status

`docs/development-continuity.md` is the handover entry point. This file summarizes the implemented domain baseline and the next planned capability block.

## Current domain baseline

Nutrition Plan / Guidance has now completed the first three roadmap capabilities:

```text
NutritionPlan domain/provenance                     implemented in PR #37
EffectiveNutritionPlan compiler                    foundation implemented in PR #37
Plan text import + explicit review/confirmation    implemented in PR #38
```

Schema progression:

```text
a8f2c6d4e1b9 -> b9e3f7c1d4a6 -> c1f4a8d2e6b9
```

PR #37 merged into `main` as `ff53a7b6f3dbb9d9acfbab6ef544ff61b7c71faa`. PR #38 was validated on code head `b283164bcd16bdcffacb47a32e0ca7e7138aa84c` with API and Web CI success; validate the exact final documentation head again before merge.

Resolve the current `main` ref directly at the start of every later session rather than treating any SHA here as permanently current.

The development/test dependency remains capped at `anyio>=4.10,<4.15` until an upstream Starlette TestClient release removes the deprecated AnyIO alias while preserving this project's warnings-as-errors policy.

## Implemented domain capabilities

### Family, Person and profile state

Implemented:

- Family and Person;
- editable Family settings and timezone;
- PersonProfile and editable energy-profile inputs;
- historical AnthropometricMeasurement records;
- NutritionGoal history;
- versioned NutritionTarget snapshots and extensible target components;
- NutritionConstraint rules with source/provenance, severity, mandatory/advisory semantics and validity dates;
- FoodPreference records and Person/Recipe preference/rating signals;
- FoodAdverseReaction records;
- ScheduleEntry planning context;
- HealthConnection and HealthMeasurement foundations;
- DailyHealthState and DailyNutritionState snapshots.

### Nutrition Plan / Guidance

Implemented foundation:

- Person-scoped `NutritionPlan` identity;
- stable lineage plus positive versioning and explicit supersession provenance;
- lifecycle states `draft`, `active`, `inactive`, `superseded`;
- source/provenance for nutritionist, clinician, user, imported and NutriFlow/system guidance;
- original source text/reference retention;
- plan validity dates;
- draft-only content mutation and active-plan immutability;
- version cloning of rule bindings and guidelines;
- historical applicability when a future version supersedes an older version;
- typed `NutritionPlanRule` binding to existing `NutritionConstraint`, `NutritionTargetComponent` or `NutritionGoal`;
- meal-context scope and local rule priority;
- plan-only vs independently applicable rule semantics;
- `NutritionPlanGuideline` for qualitative and weekly-frequency guidance;
- proposed/confirmed/rejected guideline state;
- deterministic `EffectiveNutritionPlan` compilation for Person + date + meal type;
- professional/user/imported/system ordering without silent rule deletion;
- mandatory-before-advisory ordering;
- explicit numeric-range conflict reporting;
- preservation of plan-bound target/goal snapshot semantics across later global energy-profile recalculation;
- Person-scoped plan/version/rule/guideline APIs;
- effective-plan API contract;
- migration, model/service/API tests, domain documentation and ADR-035.

### Nutrition Plan import and confirmation

Implemented in PR #38:

- `NutritionPlanImportSession` for one Person and one new draft NutritionPlan;
- parser name/version, exact source text and import lifecycle `review | applied | cancelled`;
- `NutritionPlanImportProposal` with verbatim source statement, interpretation fields, confidence, parser note and review notes;
- proposal types `numeric_rule`, `qualitative_guideline`, `frequency_guideline`, `unclassified`;
- review states `proposed`, `confirmed`, `rejected`;
- deterministic conservative parser v1 for common PT/EN nutrient values/ranges, meal scope, weekly frequencies and qualitative directives;
- explicit fallback to `unclassified` when no safe interpretation exists;
- manual proposal addition/editing during review;
- candidate-state validation before ORM mutation so invalid partial edits fail atomically;
- all proposals must be explicitly confirmed/rejected before apply;
- confirmed unclassified proposals cannot be applied until edited or rejected;
- confirmed numeric proposals materialize as `NutritionConstraint + NutritionPlanRule`;
- confirmed qualitative/frequency proposals materialize as normal confirmed `NutritionPlanGuideline` rows;
- professional/user provenance and source statement preserved through materialization;
- imported constraints bound with `applies_outside_plan=False`, preventing double counting in EffectiveNutritionPlan;
- apply leaves the NutritionPlan draft; activation remains a separate explicit operation;
- Person-scoped import list/create/read, proposal add/update, apply and cancel APIs;
- service and API tests covering parser, review gate, atomic invalid edit, materialization, activation and EffectiveNutritionPlan output;
- ADR-036 and `docs/domain/nutrition-plan-import-review.md`;
- schema revision `c1f4a8d2e6b9`.

Deferred import adapters:

- PDF/document/photo extraction;
- LLM-assisted parser implementation;
- frontend review screen under Person -> Nutrição -> Plano.

All future parser technologies must feed the same staged proposal contract and must not bypass explicit review.

### Catalogue and recipe evidence

Implemented:

- Family-owned and shared FoodItem catalogue;
- versioned FoodCompositionSnapshot nutrition evidence;
- nutrient components and explicit provenance;
- ingredient nutrition-quality/readiness states;
- Recipe CRUD/lifecycle;
- ordered RecipeIngredient editing;
- deterministic recipe nutrition calculation;
- versioned RecipeCompositionSnapshot provenance;
- exact blocking evidence for incomplete recipe nutrition;
- safe unit conversion only; no invented density;
- legacy/demo synthetic nutrition explicitly distinguished from ingredient-calculated or imported evidence;
- FoodData Central/enrichment service foundations.

### Meals, portions and planning

Implemented:

- fixed normal meal types: `breakfast`, `lunch`, `snack`, `dinner`;
- Family-scoped MealEvent;
- MealParticipant associations;
- Person-specific Serving records;
- planned/served/consumed quantities and nutrition;
- Serving nutrition provenance;
- Today/Week Family planner;
- editable/replaced/cancelled planned meals;
- idempotent planned-meal materialization;
- immutable historical serving evidence;
- deterministic DailyNutritionState recalculation from authoritative Serving history.

### Pantry and shopping

Implemented:

- quantity-aware PantryStockLot;
- expiry and active/inactive stock semantics;
- Recipe ingredient sufficiency;
- aggregate planned ingredient requirements;
- pantry subtraction after aggregate requirement calculation;
- durable ShoppingList and ShoppingListItem;
- automatic shortage items and manual household items;
- needed/purchased lifecycle;
- explicit unsafe/incomplete conversion issues.

### Recommendation engine

Implemented:

- deterministic hard-rule-first ranking;
- fail-closed handling where mandatory nutrient evidence is missing;
- existing nutrition-fit scoring;
- Person preferences and Family aggregate preference;
- practical-context filtering from schedule/location/preparation/kitchen context;
- shared-family recommendation with per-Person hard-rule evaluation;
- persisted MealRecommendationRun and MealRecommendationOption;
- append-only accepted/rejected/modified feedback;
- materialization of accepted/modified recommendations into normal MealEvent/Serving records;
- history/diversity scoring;
- strong recent-repeat penalties;
- category balance and protein rotation;
- meal-type suitability and auto-plan eligibility;
- calorie-aware and feedback-learning refinements;
- explainable score breakdowns.

Phase 4 must inspect and reuse this existing nutrition/hard-rule logic rather than build a competing evaluator. The target is one EffectiveNutritionPlan-aware MealPlanFit contract that can later feed recommendation ranking.

### Restaurant, delivery and external meals

Implemented platform abstractions:

- `MealCandidateAvailability` for `home`, `pantry`, `restaurant`, `delivery`, `store`;
- opening windows;
- `MealCommercialOffer` with provider, price, delivery fee, minimum order and validity metadata;
- provider capability/configuration separation;
- external menu ingestion that normalizes a commercial dish into FoodItem + optional FoodCompositionSnapshot + availability + offer;
- external items enter nutrition ranking only when composition evidence is present.

Provider-specific consumer discovery remains conditional on provider access/contracts. NutriFlow nutrition and Plan-Fit logic remains provider-agnostic.

### Web product baseline

Implemented information architecture direction:

```text
Início
Refeições
Pessoas
Casa
Mais
```

with progressive disclosure and focused screens rather than dashboard-heavy pages.

Key areas include:

```text
Refeições -> Hoje | Semana | Recomendar
Casa      -> Receitas | Ingredientes | Despensa | Compras | Preferências
Pessoas   -> Visão geral | Nutrição | Atividade | Saúde | Histórico | Perfil
```

Nutrition Plan belongs under:

```text
Pessoas -> <Person> -> Nutrição -> Plano
```

## Safety and correctness invariants

Preserve:

- adverse reactions and mandatory constraints before all ranking/ML;
- active professional-plan content is immutable;
- parser/AI output cannot become active guidance without explicit confirmation;
- imported content remains draft after apply until separately activated;
- missing mandatory evidence fails closed where required;
- missing evidence is unknown, never zero-filled;
- unsafe conversions are rejected rather than guessed;
- versioned nutrition provenance;
- historical Servings are never rewritten by catalogue changes;
- Family isolation;
- Person-specific portions within shared meals;
- server-authoritative nutrition/planning calculations;
- professional guidance source and priority preserved;
- conflicts surfaced rather than silently resolved;
- user rating remains distinct from recommendation score;
- demo/synthetic evidence visibly distinct from trustworthy production evidence;
- warnings are failures in validation.

## Remaining Nutrition Plan capability chain

```text
NutritionPlan                                      IMPLEMENTED
-> EffectiveNutritionPlan                         FOUNDATION IMPLEMENTED
-> plan import/parser + confirmation              IMPLEMENTED
-> evaluate candidate meal against plan           NEXT
-> explain gaps                                   NEXT
-> propose safe meal transformations              PENDING
-> use same evaluation for home/restaurant/etc.   PENDING
```

The compiler returns applicable numeric rules, goals and confirmed guidelines with provenance/conflict information. The import layer now supplies reviewed structured plan content. Neither layer claims a meal satisfies the plan; candidate evidence belongs to Meal Plan-Fit.

## Next development block

Authoritative roadmap:

`docs/vision/nutrition-plan-guidance-roadmap.md`

Recommended branch:

```text
feature/nutrition-plan-fit-evaluation
```

Target flow:

```text
Person + date + meal type
-> EffectiveNutritionPlan
+ normalized Recipe/FoodItem candidate nutrition evidence
-> mandatory-rule evaluation
-> component comparisons
-> missing-evidence reporting
-> explainable MealPlanFit result
```

Requirements:

- reuse current hard-rule/nutrition-fit logic where semantics match;
- one evaluator for recipes, home/pantry items and future restaurant/delivery candidates;
- mandatory failure must never be hidden by an average score;
- missing evidence must remain unknown, not zero;
- score is secondary to explanation;
- source/provenance should be retained in rule-level explanations;
- qualitative/frequency rules should only be evaluated when the candidate/context provides appropriate evidence;
- no provider-specific scoring engine;
- no meal transformation yet.

Trustworthy catalogue enrichment remains a parallel enabling track because precise Plan-Fit and later transformation calculations require trustworthy composition evidence.

## Broader deferred limitations

- production authentication / Family authorization;
- automatic shopping-purchase -> pantry reconciliation;
- fully trustworthy catalogue coverage;
- production-grade consumer marketplace adapters where provider access exists;
- PDF/photo/document and LLM plan parser adapters;
- frontend plan import/review screen;
- weekly frequency-progress calculation;
- Meal Plan-Fit evaluator;
- meal transformation engine;
- production npm lockfile / `npm ci` hardening.
