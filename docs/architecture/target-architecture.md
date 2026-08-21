# NutriFlow AI v2 — Target Architecture

## Architecture goals

NutriFlow AI v2 is an independent product with its own domain model, database schema, API and user experience. The architecture must support person-centric nutrition, family planning, health-data integrations, responsive UI, internationalisation and future mobile/native capabilities.

## Repository shape

```text
apps/
  api/       FastAPI application
  web/       React/TypeScript web application
  mobile/    native/mobile integration surface

packages/
  domain/    shared domain concepts and contracts
  nutrition/ nutrition calculations and rules
  health/    health-data abstractions and normalisation
  ui/        design system and reusable UI components
  i18n/      translations, locale and units
  shared/    generic shared utilities/contracts

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
```

## Domain boundaries

### People

Owns Person, demographic/profile data, goals, preferences and relationships to Family.

### Family

Owns Family membership and shared household context.

### Nutrition

Owns nutrition targets, nutrient calculations, constraints, daily nutrition state and adaptive nutrition logic.

### Food

Owns recipes, ingredients, foods/products and restaurant/delivery meals.

### Planning

Owns Meal Events, participants, planned/actual servings and meal-planning decisions.

### Health

Owns provider connections, normalised measurements, provenance, deduplication and derived health state.

### Household

Owns pantry/inventory, shopping and shared household resources.

## Intelligence layers

Recommendation logic should be layered:

1. **Hard rules** — allergies, mandatory professional constraints, impossible schedules and other non-negotiable constraints.
2. **Nutrition rules** — target ranges and safe planning constraints.
3. **Heuristics** — practical ranking based on context, pantry, time, family participation and preferences.
4. **ML ranking** — learning from accept/reject/modify behaviour and outcomes, but never bypassing hard rules.

The recommendation result should remain explainable: callers should be able to know why an option ranked well or was excluded.

## API

Initial API target remains Python + FastAPI.

API design principles:

- explicit versioned routes where necessary;
- Pydantic request/response contracts;
- domain services isolated from transport concerns;
- PostgreSQL persistence;
- migrations tracked from the beginning;
- all timestamps timezone-aware;
- health-provider payloads normalised before entering domain logic;
- secrets only through environment/configuration.

## Web

Initial web target is React + TypeScript.

Requirements:

- responsive layout from first component;
- desktop, tablet and mobile breakpoints;
- component-level accessibility;
- all user-facing strings through i18n keys;
- locale-aware dates, numbers and units;
- design tokens for spacing, colour, typography and semantic states;
- Light, Dark and System appearance modes;
- no business logic embedded in presentation components.

## Mobile

The web interface may initially cover most mobile use through responsive/PWA behaviour, but `apps/mobile` exists because native capabilities will be needed for:

- Apple HealthKit permissions and sync;
- Android Health Connect integration as required;
- background sync;
- push/local notifications;
- native device permissions.

The mobile layer should call the same API and share contracts where practical.

## Health Data Hub

Provider-specific integrations sit behind a common adapter interface.

Conceptually:

```text
Apple Health ----\
Health Connect ---\
Garmin ----------- > Provider adapters -> Normalisation -> Deduplication -> HealthMeasurement
Withings --------/
Oura ------------/
```

Each stored measurement must retain enough provenance to answer:

- whose data is this?
- what metric is it?
- what provider supplied it?
- what source device/app generated it?
- when was it measured?
- when was it imported?
- is it a duplicate/derived value?
- what confidence/quality applies?

## Adaptive state

Raw measurements should not be queried directly throughout the planner. Derived daily/rolling state should provide stable inputs such as:

- weight trend 7/28 days;
- activity trend;
- workout context;
- sleep trend;
- observed energy balance;
- planned vs consumed nutrition;
- adherence indicators.

This separates ingestion from decision-making and allows algorithms to evolve without changing provider adapters.

## Privacy model

Health connections belong to a Person and require explicit authorisation.

Family membership must not automatically grant access to another person's sensitive health measurements. Sharing and professional access require explicit permission models.

## Independence

NutriFlow AI v2 defines its own runtime, schema, API and architecture without external legacy dependencies.

Previous projects are not part of this product's domain model and no backward compatibility is assumed.
## Delivery sequence

Recommended sequence:

1. repository and architecture baseline;
2. Person + Family domain;
3. profiles, goals, constraints and schedules;
4. Recipe and Ingredient domain;
5. Meal Event + Serving + Daily Nutrition State;
6. Pantry + Shopping;
7. planner, heuristics and ML;
8. Health Data Hub and first provider;
9. Adaptive Nutrition Engine;
10. native mobile health integration and broader providers.


