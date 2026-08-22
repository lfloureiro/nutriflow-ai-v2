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
- fail-closed handling when an active mandatory nutrient maximum cannot be evaluated because candidate nutrient data is missing;
- persisted recommendation runs/options and append-only accepted/rejected/modified feedback events for future learning;
- materialization of accepted/modified recommendations into normal planned MealEvent, MealParticipant and Serving records using the exact recommendation composition snapshot;
- deterministic DailyNutritionState recalculation from authoritative Serving history using explicit local-day and target semantics;
- deterministic recommendation practical-context filtering from ScheduleEntry, location, preparation-window and kitchen availability inputs;
- fairness-first shared-family meal recommendation with person-specific portions and per-Person hard-rule evaluation;
- materialization of accepted shared-family recommendations into one MealEvent with person-specific Servings;
- Family-scoped MealEvent idempotency and immutable planned-meal replacement history for safe retries and later edits;
- persisted Family-scoped practical availability for home, pantry, restaurant, delivery and store meal sources;
- quantity-aware Family pantry stock with expiry, Recipe ingredient sufficiency and exact shopping requirements for missing quantities;
- restaurant/delivery/store opening windows plus provider-observed commercial offers with price, currency, delivery-fee, minimum-order and validity metadata;
- persisted person-scoped recommendation APIs using explicit DailyNutritionState and versioned composition evidence;
- recommendation decision API for accepted/rejected/modified persisted options, with accepted/modified decisions materialized through the standard MealEvent/MealParticipant/Serving model;
- practical recommendation orchestration combining Person schedule, home/pantry availability, pantry stock and commercial opening/offer evidence with any-source semantics;
- person-scoped planning bootstrap discovery of the latest local-day DailyNutritionState and current Family/global Food/Recipe composition evidence for the web UI;
- explicit, idempotent development demo data for exercising the real web/bootstrap/recommendation flow on a fresh local database;
- PostgreSQL persistence with Alembic migrations;
- pytest coverage with warnings treated as errors;
- Ruff static validation.

The initial web application includes:

- React + TypeScript + Vite under `apps/web`;
- responsive desktop/tablet/mobile layout;
- Portuguese and English UI strings through an i18n boundary;
- Light, Dark and System appearance modes;
- typed API client isolated from presentation code;
- Family -> Person selection followed by automatic server-authoritative planning bootstrap discovery;
- automatic DailyNutritionState selection for the chosen local meal instant;
- selectable FoodItem/Recipe names backed by current persisted composition snapshots, with technical composition UUIDs kept internal to the client;
- practical recommendation generation through the real orchestration API;
- eligible/excluded explanations, compact nutrition details and active commercial offer display;
- accept/reject actions over persisted recommendation options;
- Vitest unit tests plus strict TypeScript and production-build validation;
- a separate Web CI workflow.

The web still uses a development Family UUID entrypoint because authentication and household authorization context are not implemented yet. The meal-planning flow no longer requires users to type DailyNutritionState or composition snapshot UUIDs.

### Fresh local database

A new local database is intentionally empty. To create a synthetic development Family, Person, current DailyNutritionState and six meal candidates:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\api
python -m app.demo_seed
```

The command is explicit and idempotent; startup never auto-seeds. It prints the Family ID required by the current web development entrypoint. See `docs/domain/development-demo-dataset.md` and ADR-033.

Detailed domain status is maintained in `docs/domain/implementation-status.md`. Web flow decisions are documented under `docs/ux/` and `docs/decisions/`.

For a later development session, start with `docs/development-continuity.md`. It records the current checkpoint, exact resumption procedure, migration/test baseline and next safe development step.

## Development workflow

Changes are developed on focused branches rather than directly on `main`.

Before a branch is integrated it must:

- update relevant documentation and the continuity checkpoint;
- include or update tests;
- validate migrations locally when the database changes;
- pass the relevant local validation gates with zero warnings;
- open a PR only after local validation is green;
- pass CI on the exact PR head SHA;
- be squash-merged only after the tested head is confirmed unchanged.

The authoritative workflow decision is documented in `docs/decisions/ADR-007-development-workflow-and-ci.md`.

GitHub Actions runs API migration/Ruff/pytest validation and a separate web test/type-check/production-build gate.
