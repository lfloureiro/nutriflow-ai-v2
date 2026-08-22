# NutriFlow AI v2

NutriFlow AI v2 is a standalone, person-centric adaptive nutrition platform for individuals and families.

## Product direction

The core model is based on:

Person -> Family -> Health -> Schedule -> Meals -> Nutrition State -> Feedback

The system is designed to support:

- Individual nutrition profiles
- Family and shared meals
- Individual portions
- Dietary preferences and restrictions
- Medical and nutritionist-defined constraints
- Personal schedules
- Activity and health data
- Adaptive nutrition planning
- Recipes, pantry and shopping
- Restaurant and delivery meals
- Machine-learning-assisted meal selection

## Platform principles

NutriFlow AI v2 is designed from the beginning for:

- Multilingual support
- Light, dark and system themes
- Desktop and mobile layouts
- Responsive UI
- Web and native/mobile integration
- Apple Health / HealthKit
- Android Health Connect
- Future wearable and health-provider integrations

## Repository structure

apps/
  api/
  web/
  mobile/

packages/
  domain/
  nutrition/
  health/
  ui/
  i18n/
  shared/

database/
  migrations/
  seeds/

docs/
  vision/
  architecture/
  domain/
  ux/
  decisions/

tests/
tools/

## Current implementation status

The current backend foundation includes:

- Family and Person;
- PersonProfile;
- historical anthropometric measurements;
- NutritionGoal history;
- NutritionConstraint rules and provenance;
- FoodPreference records;
- FoodAdverseReaction records for allergies and intolerances;
- ScheduleEntry records for recurring and one-off availability context;
- versioned NutritionTarget snapshots with extensible nutrient components;
- person-scoped HealthConnection records for health-provider integrations;
- normalized HealthMeasurement records with provenance and cross-path deduplication identity;
- versioned DailyHealthState and DailyNutritionState snapshots with extensible nutrient progress components;
- family-scoped MealEvent records with MealParticipant associations;
- person-specific Serving records with planned, served and consumed quantities and nutrition components;
- FoodItem catalogue records with versioned FoodCompositionSnapshot nutrition data;
- Recipe and RecipeIngredient records with versioned RecipeCompositionSnapshot nutrition data;
- optional Serving links to FoodItem or Recipe while preserving historical serving snapshots;
- explicit Serving nutrition calculation from versioned catalogue composition with conservative unit conversion and persisted calculation provenance;
- deterministic meal recommendation ranking with hard-rule-first safety, nutrition fit, preferences and explainable scoring;
- persisted recommendation runs/options and append-only accepted/rejected/modified feedback events for future learning;
- materialization of accepted/modified recommendations into normal planned MealEvent, MealParticipant and Serving records using the exact recommendation composition snapshot;
- deterministic DailyNutritionState recalculation from authoritative Serving history using explicit local-day and target semantics;
- deterministic recommendation practical-context filtering from ScheduleEntry, location, preparation-window and kitchen availability inputs;
- fairness-first shared-family meal recommendation with person-specific portions and per-Person hard-rule evaluation;
- materialization of accepted shared-family recommendations into one planned MealEvent with person-specific MealParticipant and Serving records;
- Family-scoped MealEvent idempotency and immutable planned-meal replacement history for safe retries and later edits;
- persisted Family-scoped practical availability for home, pantry, restaurant, delivery and store meal sources;
- quantity-aware Family pantry stock with expiry, Recipe ingredient sufficiency and exact shopping requirements for missing quantities;
- restaurant/delivery/store opening windows plus provider-observed commercial offers with price, currency, delivery-fee, minimum-order and validity metadata;
- PostgreSQL persistence with Alembic migrations;
- pytest coverage with warnings treated as errors;
- Ruff static validation.

Detailed domain status is maintained in `docs/domain/implementation-status.md`.

For a later development session, start with `docs/development-continuity.md`. It records the current checkpoint, exact resumption procedure, migration/test baseline and next safe development step.

## Development workflow

Changes are developed on focused branches rather than directly on `main`.

Before a branch is integrated it must:

- update relevant documentation and the continuity checkpoint;
- include or update tests;
- validate migrations locally when the database changes;
- pass Ruff and the complete local test suite with zero warnings;
- open a PR only after local validation is green;
- pass CI on the exact PR head SHA;
- be squash-merged only after the tested head is confirmed unchanged.

The authoritative workflow decision is documented in `docs/decisions/ADR-007-development-workflow-and-ci.md`.

GitHub Actions runs Ruff, the API test suite against PostgreSQL, and verifies that the Alembic migration chain is current.
