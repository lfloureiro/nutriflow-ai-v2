# Domain implementation status

`docs/development-continuity.md` is the handover entry point. This file summarizes the implemented domain baseline and the next planned capability block.

## Current domain baseline

The Nutrition Plan / Guidance foundation was built from verified `main` SHA `9d82a148992a788d484e28d21f595724530ae9d5` in PR #37.

Schema progression for this block:

```text
a8f2c6d4e1b9 -> b9e3f7c1d4a6
```

Resolve the current `main` ref directly at the start of every later session rather than treating any SHA in this document as permanently current.

The development/test dependency remains capped at `anyio>=4.10,<4.15` until an upstream Starlette TestClient release removes the deprecated AnyIO alias while preserving this project's warnings-as-errors validation policy.

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

Implemented:

- Person-scoped `NutritionPlan` identity;
- stable lineage plus positive versioning and explicit supersession provenance;
- lifecycle states: `draft`, `active`, `inactive`, `superseded`;
- source/provenance for nutritionist, clinician, user, imported and NutriFlow/system guidance;
- original source text/reference retention;
- plan validity dates;
- draft-only content mutation and active-plan immutability;
- version cloning of rule bindings and guidelines;
- historical date applicability when a future version supersedes an older version;
- typed `NutritionPlanRule` binding to existing `NutritionConstraint`, `NutritionTargetComponent` or `NutritionGoal`;
- meal-context scope and local rule priority;
- plan-only vs independently applicable rule semantics;
- `NutritionPlanGuideline` for qualitative and weekly-frequency guidance;
- proposed/confirmed/rejected guideline state;
- deterministic `EffectiveNutritionPlan` compilation for Person + date + meal type;
- explicit professional/user/imported/system ordering without silent rule deletion;
- mandatory-before-advisory ordering;
- explicit numeric-range conflict reporting;
- preservation of plan-bound target/goal snapshot semantics across later global energy-profile recalculation;
- Person-scoped plan/version/rule/guideline APIs;
- effective-plan API contract;
- migration, model/service/API tests, domain documentation and ADR-035.

Not implemented yet:

- plan text/document parser;
- proposal confidence/evidence model;
- explicit parser review/confirmation UI;
- weekly guideline progress calculation;
- meal-candidate Plan-Fit;
- Meal Transformation.

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
- nutrition-fit scoring;
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

### Restaurant, delivery and external meals

Implemented platform abstractions:

- `MealCandidateAvailability` for `home`, `pantry`, `restaurant`, `delivery`, `store`;
- opening windows;
- `MealCommercialOffer` with provider, price, delivery fee, minimum order and validity metadata;
- provider capability/configuration separation;
- external menu ingestion that normalizes a commercial dish into FoodItem + optional FoodCompositionSnapshot + availability + offer;
- external items enter nutrition ranking only when composition evidence is present.

Provider-specific consumer discovery remains conditional on provider access/contracts. NutriFlow nutrition and Plan-Fit logic must remain provider-agnostic.

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

The future plan UI belongs under:

```text
Pessoas -> <Person> -> Nutrição -> Plano
```

## Safety and correctness invariants

Preserve:

- adverse reactions and mandatory constraints before all ranking/ML;
- active professional-plan content is immutable;
- parser/AI output cannot become active guidance without explicit confirmation;
- missing mandatory evidence fails closed where required;
- missing evidence is unknown, never zero-filled;
- unsafe conversions are rejected rather than guessed;
- versioned nutrition provenance;
- historical Servings never rewritten by catalogue changes;
- Family isolation;
- Person-specific portions within shared meals;
- server-authoritative nutrition/planning calculations;
- professional guidance source and priority preserved;
- conflicts surfaced rather than silently resolved;
- user rating remains distinct from recommendation score;
- demo/synthetic evidence visibly distinct from trustworthy production evidence;
- warnings are failures in validation.

## Remaining Nutrition Plan capability chain

The first two roadmap capabilities now exist:

```text
NutritionPlan                                      IMPLEMENTED
-> EffectiveNutritionPlan                         FOUNDATION IMPLEMENTED
-> plan import/parser + confirmation              NEXT
-> evaluate candidate meal against plan           PENDING
-> explain gaps                                   PENDING
-> propose safe meal transformations              PENDING
-> use same evaluation for home/restaurant/etc.   PENDING
```

The effective compiler can already return applicable numeric rules, goals and confirmed guidelines with provenance and conflict information. It deliberately does not claim a candidate meal satisfies those requirements; candidate evidence belongs to Meal Plan-Fit.

## Next development block

Authoritative roadmap:

`docs/vision/nutrition-plan-guidance-roadmap.md`

Recommended branch:

```text
feature/nutrition-plan-import-confirmation
```

Scope:

```text
raw source text/document reference
-> parser output as proposed interpretations
-> mapping proposal to reusable rule/guideline semantics
-> confidence/evidence metadata
-> explicit user review/edit/confirm/reject
-> confirmed structured plan content only after approval
```

The parser must never directly activate a rule. Preserve the original statement beside every interpretation so review remains explainable.

Do not begin Meal Transformation or provider-specific work in this block. Meal Plan-Fit follows after parser/confirmation semantics are stable.

Trustworthy catalogue enrichment remains a parallel enabling track because precise future meal-fit and transformation calculations require trustworthy composition evidence.

## Broader deferred limitations

- production authentication / Family authorization;
- automatic shopping-purchase -> pantry reconciliation;
- fully trustworthy catalogue coverage;
- production-grade consumer marketplace adapters where provider access exists;
- professional-plan parser/confirmation flow;
- weekly frequency-progress calculation;
- Meal Plan-Fit evaluator;
- meal transformation engine;
- production npm lockfile / `npm ci` hardening.
