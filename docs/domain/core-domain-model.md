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
- health-data connections.

### Family

Represents a group of people who share household and meal context.

A Person may belong to a Family, but nutrition requirements remain person-specific.

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

### Recipe / Ingredient / Food

Food is a native NutriFlow AI v2 domain covering recipes, ingredients, products and external meal sources.

The Food/Recipe catalogue is a separate next domain layer. Meal history must remain stable even when catalogue data changes later.

### Pantry / Inventory

Shared household availability of food/product items.

### ShoppingList

Derived or user-managed shopping requirements supporting planned meals and pantry state.

## Key relationships

```text
Family
  1 -> many Person memberships
  1 -> many MealEvents

Person
  1 -> many Goals
  1 -> many NutritionConstraints
  1 -> many Schedule entries
  1 -> many HealthDataConnections
  1 -> many HealthMeasurements
  1 -> many DailyHealthStates
  1 -> many DailyNutritionStates
  1 -> many MealParticipants

MealEvent
  1 -> many MealParticipants

MealParticipant
  belongs to one MealEvent
  belongs to one Person
  1 -> many Servings

Serving
  1 -> many ServingNutritionComponents

Family
  1 -> shared Pantry
  1 -> many ShoppingLists
```

## Meal planning rule

The planner should optimise across the person's day and family context, not treat each meal slot independently.

A future family dinner can therefore influence an earlier individual lunch or snack because planned person-specific Servings contribute to DailyNutritionState.

The meal occasion may be shared while portions remain individual.

## Safety rule

Hard constraints are evaluated before ranking or ML. An option that violates a mandatory allergy or clinician constraint is excluded, not merely down-ranked.
