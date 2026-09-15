# Domain implementation status

`docs/development-continuity.md` is the handover entry point. This file summarizes the integrated domain baseline and the next planned capability block.

## Current integrated baseline

Current verified `main` at the documentation rebaseline point:

```text
main SHA:    cbb09ad1d5e079e6b73ada2ebcc25999b80eca9c
schema head: a8f2c6d4e1b9
API CI:      success on exact main SHA
Web CI:      success on exact main SHA
```

There is no open pull request representing unfinished product work at this checkpoint. Old feature branches are historical refs unless a new PR explicitly reactivates them.

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

Provider-specific consumer discovery remains conditional on provider access and contracts. The NutriFlow domain must remain provider-agnostic.

### Web product baseline

Implemented direction:

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

## Safety and correctness invariants

Preserve:

- adverse reactions and mandatory constraints before all ranking/ML;
- missing mandatory evidence fails closed where required;
- missing evidence is unknown, never zero-filled;
- unsafe conversions rejected rather than guessed;
- versioned nutrition provenance;
- historical Servings never rewritten by catalogue changes;
- Family isolation;
- Person-specific portions within shared meals;
- server-authoritative nutrition/planning calculations;
- professional guidance source and priority preserved;
- user rating remains distinct from recommendation score;
- demo/synthetic evidence visibly distinct from trustworthy production evidence;
- warnings are failures in validation.

## Principal capability gap

The current models represent goals, targets and individual constraints, but there is no first-class object representing a coherent **Nutrition Plan** supplied by a nutritionist/clinician/user and no compiler that resolves that plan into meal-context guidance.

The missing product chain is:

```text
NutritionPlan
-> structured plan rules / targets / guidelines
-> EffectiveNutritionPlan for Person + date + meal context
-> evaluate any meal against that effective plan
-> explain gaps
-> propose safe meal transformations
-> use the same evaluation for home, recipe, restaurant and delivery candidates
```

Do not solve this by overloading every qualitative or frequency rule into `NutritionConstraint`. The new plan layer must be able to represent at least:

- mandatory constraints;
- numeric targets/ranges;
- meal-specific targets;
- qualitative guidance/preferences;
- weekly frequency guidance;
- provenance and priority;
- version/lifecycle and date validity;
- original source text/document reference;
- distinction between professionally prescribed, user-authored and NutriFlow-derived guidance.

## Next development programme

Authoritative roadmap:

`docs/vision/nutrition-plan-guidance-roadmap.md`

Order:

```text
1. NutritionPlan domain
2. EffectiveNutritionPlan compiler
3. plan import/parser + confirmation
4. Meal Plan-Fit evaluation
5. Meal Transformation
6. home/pantry recommendations
7. restaurant/delivery recommendations
8. weekly adaptive planning
9. feedback/learning refinement
```

Trustworthy catalogue enrichment should continue as a parallel enabling track because precise meal-fit and transformation calculations require trustworthy composition evidence.

## Immediate next block

Recommended branch:

```text
feature/nutrition-plan-guidance-foundation
```

First block should implement domain + compiler only, with migrations/tests/docs and no dependency on external provider APIs.

Expected first-block concepts:

```text
NutritionPlan
NutritionPlanRule / guideline representation
plan provenance + version/lifecycle
meal-context applicability
EffectiveNutritionPlan
```

Existing `NutritionConstraint`, `NutritionTarget` and `NutritionGoal` should be reused where semantically correct rather than duplicated.

## Broader deferred limitations

- production authentication / Family authorization;
- automatic shopping-purchase -> pantry reconciliation;
- fully trustworthy catalogue coverage;
- production-grade consumer marketplace adapters where provider access exists;
- professional-plan document ingestion/parser;
- meal transformation engine;
- production npm lockfile / `npm ci` hardening.
