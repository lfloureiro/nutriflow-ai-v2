# Domain implementation status

This document tracks the implemented domain baseline so code, migrations, tests and domain documentation evolve together.

## Implemented foundation

### Family and Person

Implemented:

- Family aggregate root;
- Person linked to Family;
- locale and timezone support;
- API routes and services for Family and Person;
- persistence and tests.

### Person profile and anthropometric history

Implemented:

- one-to-one PersonProfile;
- energy-calculation sex, measurement system and energy unit;
- historical AnthropometricMeasurement records;
- metric, value, unit, observed time and provenance;
- persistence and tests.

### Nutrition goals and constraints

Implemented:

- historical NutritionGoal records;
- target weight/rate and validity semantics;
- NutritionConstraint rules with minimum/maximum/exclusion semantics;
- mandatory versus advisory constraints;
- professional provenance and validity periods;
- database validation, persistence and tests.

### Food preferences and adverse reactions

Implemented separately:

- FoodPreference records for likes/dislikes and intensity;
- FoodAdverseReaction records for allergy/intolerance safety semantics;
- provenance and validity dates;
- persistence and tests.

Preference ranking is intentionally separate from food-safety exclusion.

### Person schedule

Implemented:

- recurring and one-off ScheduleEntry shapes;
- availability effects;
- recurrence-rule storage;
- timezone-aware date/time semantics;
- flexibility, location, provenance and notes;
- database validation, persistence and tests.

Detailed semantics: `docs/domain/schedule-model.md`.

### Nutrition targets

Implemented:

- versioned NutritionTarget snapshots per Person;
- optional relationship to NutritionGoal;
- BMR/TDEE estimates and methods;
- target energy range;
- calculation version and input provenance;
- extensible NutritionTargetComponent nutrient targets;
- historical validity and persistence tests.

Detailed semantics: `docs/domain/nutrition-target-model.md` and ADR-008.

### Health connections and normalized measurements

Implemented:

- Person-scoped HealthConnection records;
- provider-agnostic connection lifecycle, permissions and sync metadata;
- secret-free credential references;
- normalized HealthMeasurement records;
- point and interval measurement shapes;
- provider/origin/source-chain provenance;
- deterministic cross-path deduplication;
- historical preservation when a connection is removed;
- persistence and tests.

Detailed semantics: `docs/domain/health-connection-model.md`, `docs/domain/health-measurement-model.md`, ADR-009 and ADR-010.

### Daily health and nutrition state

Implemented:

- versioned DailyHealthState snapshots per Person/local date;
- weight, activity, energy, sleep, heart-rate/HRV and training context;
- confidence and source-window metadata;
- versioned DailyNutritionState snapshots;
- consumed, planned and remaining energy;
- nutrient-level DailyNutritionStateComponent values;
- calculation versions and explainable inputs;
- persistence and tests.

Daily states remain recalculable derived data rather than authoritative source history.

Detailed semantics: `docs/domain/daily-state-model.md` and ADR-011.

### Meal events, participants and servings

Implemented:

- Family-scoped MealEvent records;
- one shared MealEvent with multiple MealParticipant records;
- person-specific participation states;
- multiple Serving records per participant;
- planned, served and consumed quantities and energy;
- ServingNutritionComponent nutrient values;
- replacement history and partial-consumption tracking;
- database constraints, persistence and tests.

There is intentionally no separate SharedMeal table. Shared context lives on MealEvent while nutrition remains person-specific through Serving.

Detailed semantics: `docs/domain/meal-model.md` and ADR-012.

### Food, ingredient and recipe catalogue

Implemented:

- FoodItem identities for ingredients, products, dishes, beverages, supplements and generic foods;
- global or Family-specific catalogue records;
- versioned FoodCompositionSnapshot records;
- extensible FoodNutrientComponent records;
- Recipe and RecipeIngredient records;
- versioned RecipeCompositionSnapshot and RecipeNutrientComponent records;
- optional Serving links to either FoodItem or Recipe;
- historical Serving values protected from later catalogue corrections;
- persistence and tests.

Detailed semantics: `docs/domain/food-catalog-model.md` and ADR-013.

### Serving nutrition calculation

Implemented on the current feature branch:

- calculation of planned, served and consumed Serving energy from an explicitly selected FoodCompositionSnapshot or RecipeCompositionSnapshot;
- scaling of all nutrient components from the same versioned composition;
- Decimal arithmetic with explicit persisted precision;
- safe mass conversion between `mg`, `g` and `kg`;
- safe volume conversion between `ml` and `l`;
- exact-unit support for other units without implicit conversion;
- rejection of cross-dimension conversions and inferred density;
- validation that the selected composition belongs to the Serving FoodItem or Recipe;
- persisted composition-snapshot provenance on Serving;
- persisted `nutrition_calculation_version`;
- recalculation replacing stale materialized nutrient components only when explicitly requested;
- tests for scaling, unit conversion safety and catalogue mismatch rejection.

Detailed semantics: `docs/domain/serving-nutrition-calculation.md` and ADR-014.

## Current database migration chain

The schema currently progresses through:

1. Family/Person;
2. Person profile and anthropometric history;
3. nutrition goals and constraints;
4. food preferences/adverse reactions;
5. schedules;
6. NutritionTarget;
7. HealthConnection;
8. HealthMeasurement;
9. DailyHealthState/DailyNutritionState;
10. MealEvent/MealParticipant/Serving;
11. Food/Recipe catalogue composition;
12. Serving composition provenance.

Alembic migrations are expected to apply from an empty PostgreSQL database in CI and `alembic check` must report no model/schema drift.

## Next planned domain increments

Current sequence after the serving-nutrition calculation layer:

1. adaptive meal planning and recommendation services;
2. automatic DailyNutritionState recalculation from authoritative Serving history;
3. restaurant and delivery meal sources;
4. pantry and shopping integration;
5. API and UI vertical slices over the completed planning flow;
6. richer catalogue metadata, multilingual presentation and explicit household-unit/density conversions.

Each increment must be developed on a focused branch, documented, tested locally with zero warnings, validated by CI and merged only after all checks are green.
