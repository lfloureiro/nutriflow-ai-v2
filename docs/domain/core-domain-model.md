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

Suggested fields:

- person_id;
- constraint_type;
- nutrient/food target where applicable;
- operator (min/max/exclude/etc.);
- value and unit;
- severity/priority;
- source (`user`, `doctor`, `nutritionist`, `system`);
- start/end dates;
- notes;
- active flag.

### Goal

A time-aware goal such as weight loss, maintenance, muscle gain or performance.

Goals should preserve assumptions and expected rate/range instead of only a final calorie number.

### MealEvent

Represents an eating occasion.

Suggested fields:

- date/time;
- meal type;
- participants;
- location;
- source;
- recipe/food reference;
- status (planned, consumed, skipped, replaced);
- notes.

### MealParticipant

Links a Person to a MealEvent and holds participation-specific state.

### Serving

The portion assigned/planned/consumed by one person for one MealEvent.

Allows a shared family recipe to produce different quantities and nutrition for different participants.

### DailyNutritionState

Derived per-person state for one day, including:

- target energy and nutrients;
- consumed totals;
- planned future totals;
- remaining target/ranges;
- activity/training context;
- confidence/adherence signals.

### HealthDataConnection

One Person's authorised connection to an external health provider.

Examples: Apple Health, Health Connect, Garmin, Withings, Oura, Fitbit.

### HealthMeasurement

Normalised observation imported from a provider.

Suggested fields:

- person_id;
- metric_type;
- value/unit;
- measured_at;
- provider;
- source_device/source_app;
- external_id;
- imported_at;
- quality/confidence;
- deduplication metadata.

### DailyHealthState

Derived health context used by planning rather than raw provider records.

Possible derived fields:

- latest weight;
- 7/28-day weight trend;
- body composition trend;
- active energy/activity trend;
- workouts/training load context;
- sleep duration/consistency trend;
- resting HR/HRV context where justified;
- observed energy-balance estimate;
- data completeness/confidence.

### Recipe / Ingredient / Food

Food model reused or adapted from NutriFlow v1 after review.

### Pantry / Inventory

Shared household availability of food/product items.

### ShoppingList

Derived or user-managed shopping requirements supporting planned meals and pantry state.

## Key relationships

```text
Family
  1 -> many Person memberships

Person
  1 -> many Goals
  1 -> many NutritionConstraints
  1 -> many Schedule entries
  1 -> many HealthDataConnections
  1 -> many HealthMeasurements
  1 -> many DailyHealthStates
  1 -> many DailyNutritionStates

MealEvent
  many <-> many Person via MealParticipant
  1 -> many Servings

Serving
  belongs to one MealEvent
  belongs to one Person

Family
  1 -> shared Pantry
  1 -> many ShoppingLists
```

## Planning rule

The planner should optimise across the person's day and family context, not treat each meal slot independently.

A future family dinner can therefore influence an earlier individual lunch or snack because planned nutrition is included in the DailyNutritionState.

## Safety rule

Hard constraints are evaluated before ranking or ML. An option that violates a mandatory allergy or clinician constraint is excluded, not merely down-ranked.
