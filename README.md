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
- PostgreSQL persistence with Alembic migrations;
- pytest coverage with warnings treated as errors;
- Ruff static validation.

Detailed domain status is maintained in `docs/domain/implementation-status.md`.

## Development workflow

Changes are developed on focused branches rather than directly on `main`.

Before a branch is integrated it must:

- update relevant documentation;
- include or update tests;
- validate migrations locally when the database changes;
- pass Ruff and the complete local test suite with zero warnings;
- pass CI verification.

The workflow decision is documented in `docs/decisions/ADR-007-development-workflow-and-ci.md`.

GitHub Actions runs Ruff, the API test suite against PostgreSQL, and verifies that the Alembic migration chain is current.
