# NutriFlow AI v2

NutriFlow AI v2 is the next-generation, person-centric evolution of NutriFlow.

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
  legacy-v1/

docs/
  vision/
  architecture/
  domain/
  ux/
  decisions/

tests/
tools/

## Status

Initial architecture and product definition.
NutriFlow v1 remains the reference implementation for proven functionality that may be selectively migrated into v2.
