# NutriFlow AI v2 — Core Domain Model

## Core entities

### Person

Represents one individual whose nutrition is planned and evaluated.

Key concepts:

- demographic/profile data;
- body measurements and history;
- activity assumptions;
- goals;
- preferences;
- allergies/intolerances;
- professional nutrition constraints;
- schedules;
- locale and units;
- health-data connections;
- recommendation history and feedback.

### Family

Represents a group of people who share household and meal context.

A Person may belong to a Family, but nutrition requirements remain person-specific.

Family can also own household-specific FoodItems and Recipes while globally reusable catalogue entries remain unscoped.

### PersonSchedule

Represents recurring and exceptional availability/context such as:

- work/school;
- usual meal windows;
- training;
- travel;
- family meal opportunities.

Schedule data helps determine whether a meal is individual or shared and what practical options are possible.

### NutritionConstraint

Structured rule rather than free text.

Core fields include:

- person_id;
- constraint type;
- nutrient/food target where applicable;
- operator;
- value and unit;
- severity/priority;
- source (`user`, `doctor`, `nutritionist`, `system`);
- validity dates;
- notes.

### Goal

A time-aware goal such as weight loss, maintenance, muscle gain or performance.

Goals preserve assumptions and expected rate/range instead of only a final calorie number.

### MealEvent

Represents one eating occasion in Family context.

A MealEvent may be individual or shared.

Shared meals are not a separate entity: one MealEvent becomes shared when it has multiple MealParticipant records.

Core fields include:

- family_id;
- scheduled date/time and timezone;
- meal type;
- title;
- lifecycle status;
- served/completed timestamps;
- replacement linkage;
- location;
- source/reference;
- notes.

### MealParticipant

Links one Person to one MealEvent and holds person-specific participation state.

Examples include planned, served, consumed, partial, skipped and replaced.

One Person may occur only once in the same MealEvent.

### Serving

Represents one person-specific food/dish portion for a MealParticipant.

A participant may have multiple Servings in one meal.

Serving keeps planned, served and consumed quantities and energy separate so NutriFlow can compare intent, preparation and actual intake.

Serving belongs to MealParticipant rather than independently storing MealEvent and Person foreign keys. MealParticipant already defines both identities and therefore prevents inconsistent combinations.

A Serving may optionally reference one FoodItem or one Recipe. It still stores its own historical item identity and nutrition snapshot so future catalogue updates do not rewrite past intake.

### ServingNutritionComponent

Stores extensible nutrient-level planned, served and consumed values for a Serving.

Energy remains directly available on Serving for frequent daily aggregation, while nutrients such as protein, fibre or sodium use component records.

### DailyNutritionState

Derived per-person state for one day, including:

- target energy and nutrients;
- consumed totals;
- planned future totals;
- remaining target/ranges;
- activity/training context;
- confidence/adherence signals.

DailyNutritionState is recalculable from NutritionTarget plus authoritative meal/serving history.

### HealthDataConnection

One Person's authorised connection to an external health provider.

Examples: Apple Health, Health Connect, Garmin, Withings, Oura, Fitbit.

### HealthMeasurement

Normalised observation imported from a provider with provenance and deduplication identity.

### DailyHealthState

Derived health context used by planning rather than raw provider records.

Possible fields include:

- latest weight;
- 7/28-day weight trend;
- active energy/activity context;
- workouts/training load;
- sleep context;
- resting HR/HRV context;
- data completeness/confidence.

### FoodItem

Stable catalogue identity for an ingredient, packaged product, dish, beverage, supplement or generic food.

FoodItem can be global or Family-specific and has a stable catalogue key plus source metadata.

Nutrition values are not mutable fields on FoodItem.

### FoodCompositionSnapshot

Versioned nutrition composition for one FoodItem reference quantity/unit.

It stores energy directly and extensible FoodNutrientComponent children for nutrient values.

A new source version creates a new snapshot rather than changing historical composition.

### Recipe

Reusable preparation definition containing yield metadata and ordered RecipeIngredient records.

Recipes can be global or Family-specific.

### RecipeIngredient

Links a Recipe to a FoodItem quantity and unit.

### RecipeCompositionSnapshot

Versioned derived composition for a Recipe reference quantity/unit.

It stores calculation version/input provenance so NutriFlow can explain which Food composition versions produced a recipe result.

RecipeNutrientComponent provides extensible nutrient values.

### MealRecommendationRun

Person-scoped record of one recommendation-engine execution for one planning date.

It preserves the engine version, optional DailyNutritionState reference, optional meal type and context used to produce the recommendation set.

### MealRecommendationOption

Historical snapshot of one candidate evaluated during a MealRecommendationRun.

It preserves:

- candidate identity and quantity;
- eligibility;
- rank and score when eligible;
- score breakdown and explanations;
- mandatory exclusion reasons;
- candidate subjects used by rule matching;
- the nutrition snapshot used for evaluation;
- optional FoodItem/Recipe and composition-snapshot provenance.

Excluded options remain in history for auditability but are not user-feedback targets.

### MealRecommendationFeedback

Append-only accepted/rejected/modified event attached to an eligible MealRecommendationOption.

It may link to the resulting Serving when an accepted or modified recommendation has already been materialized.

Feedback is a learning signal, not an eligibility rule.

### Pantry / Inventory

Shared household availability of food/product items.

### ShoppingList

Derived or user-managed shopping requirements supporting planned meals and pantry state.

## Key relationships

```text
Family
  1 -> many Person memberships
  1 -> many MealEvents
  1 -> many household FoodItems
  1 -> many household Recipes

Person
  1 -> many Goals
  1 -> many NutritionConstraints
  1 -> many Schedule entries
  1 -> many HealthDataConnections
  1 -> many HealthMeasurements
  1 -> many DailyHealthStates
  1 -> many DailyNutritionStates
  1 -> many MealParticipants
  1 -> many MealRecommendationRuns

FoodItem
  1 -> many FoodCompositionSnapshots
  1 -> many RecipeIngredients

FoodCompositionSnapshot
  1 -> many FoodNutrientComponents

Recipe
  1 -> many RecipeIngredients
  1 -> many RecipeCompositionSnapshots

RecipeCompositionSnapshot
  1 -> many RecipeNutrientComponents

MealEvent
  1 -> many MealParticipants

MealParticipant
  belongs to one MealEvent
  belongs to one Person
  1 -> many Servings

Serving
  optionally -> one FoodItem OR one Recipe
  1 -> many ServingNutritionComponents

MealRecommendationRun
  belongs to one Person
  optionally -> one DailyNutritionState
  1 -> many MealRecommendationOptions

MealRecommendationOption
  optionally -> one FoodItem OR one Recipe
  optionally -> one FoodCompositionSnapshot OR one RecipeCompositionSnapshot
  1 -> many MealRecommendationFeedback events

MealRecommendationFeedback
  optionally -> one resulting Serving

Family
  1 -> shared Pantry
  1 -> many ShoppingLists
```

## Meal planning rule

The planner should optimise across the person's day and family context, not treat each meal slot independently.

A future family dinner can therefore influence an earlier individual lunch or snack because planned person-specific Servings contribute to DailyNutritionState.

The meal occasion may be shared while portions remain individual.

## Recommendation history rule

Recommendation output is historical decision data.

A recommendation option copies the candidate identity, nutrition snapshot, eligibility and explanation used at recommendation time. Later catalogue updates or algorithm changes must not rewrite what the person actually saw.

Feedback is append-only so a later modification does not erase an earlier acceptance.

## Catalogue history rule

Current Food/Recipe knowledge and historical intake are separate responsibilities.

Catalogue composition is versioned. A Serving copies the nutrition values used for that planned/served/consumed portion and may retain a catalogue reference for provenance.

Changing a FoodItem, FoodCompositionSnapshot selection or Recipe composition later must not silently alter old Serving records.

## Safety rule

Hard constraints are evaluated before ranking or ML. An option that violates a mandatory allergy or clinician constraint is excluded, not merely down-ranked.

Recommendation feedback and future learned ranking may influence ordering only among candidates that already passed deterministic eligibility checks.
