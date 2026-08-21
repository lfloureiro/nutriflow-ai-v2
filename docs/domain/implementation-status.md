# Domain implementation status

This document tracks the implemented domain baseline so the code and domain documentation evolve together.

## Implemented foundation

### Family and Person

Implemented:

- Family aggregate root;
- Person linked to Family;
- locale and timezone support;
- API routes and services for Family and Person;
- persistence and tests.

### Person profile

Implemented:

- one-to-one PersonProfile;
- sex used for energy calculations;
- measurement system;
- energy unit;
- persistence and tests.

### Anthropometric history

Implemented:

- historical AnthropometricMeasurement records;
- metric, value, unit and measured timestamp;
- provenance fields for provider/device/external identifiers;
- ordered Person relationship;
- persistence and tests.

### Nutrition goals

Implemented:

- historical NutritionGoal records;
- goal type;
- optional target weight;
- optional target rate;
- start and target dates;
- status, source and notes;
- database validation for positive target values and valid date ordering;
- persistence and tests.

### Nutrition constraints

Implemented:

- NutritionConstraint records per Person;
- constraint and target types;
- target key and operator;
- minimum/maximum values and units;
- severity and mandatory/advisory distinction;
- provenance including professional source metadata;
- optional validity period;
- database validation for numeric ranges and date ordering;
- persistence and tests.

### Food preferences

Implemented:

- FoodPreference records per Person;
- subject type and normalized subject key;
- like/dislike preference type;
- preference intensity;
- provenance and optional validity dates;
- persistence and tests.

### Food adverse reactions

Implemented separately from preferences:

- FoodAdverseReaction records per Person;
- allergy/intolerance reaction type;
- subject type and normalized subject key;
- severity;
- mandatory safety flag;
- provenance including professional source metadata;
- optional validity dates;
- persistence and tests.

The separation between preferences and adverse reactions is intentional: preference ranking must never be confused with food safety restrictions.

### Person schedule

Implemented:

- ScheduleEntry records per Person;
- separate recurring and one-off entry shapes;
- extensible event types;
- explicit availability effects;
- RFC 5545-style recurrence-rule storage;
- recurring local times with validity dates;
- timezone-aware one-off timestamps;
- explicit timezone context;
- non-negative flexibility in minutes;
- optional location, source reference and notes;
- database validation for entry shape, date ranges, timestamp ranges and availability values;
- persistence and tests.

Date-specific one-off entries are more specific than recurring patterns when planning logic resolves conflicting availability.

Detailed schedule semantics are documented in `docs/domain/schedule-model.md`.

### Nutrition targets

Implemented:

- versioned NutritionTarget snapshots per Person;
- optional relationship to the NutritionGoal that informed the calculation;
- explicit validity period and lifecycle status;
- BMR estimate and calculation method;
- TDEE estimate and calculation method;
- target energy range;
- calculation-version identifier;
- calculation-input provenance for explainability;
- extensible NutritionTargetComponent child records for nutrient targets;
- minimum, maximum and point-target component values;
- database validation for positive energy values, valid ranges and non-empty components;
- uniqueness of target type/key within each snapshot;
- historical ordering by validity start date;
- persistence and tests.

Nutrition targets are derived outputs. They remain separate from NutritionGoal, NutritionConstraint and DailyNutritionState concepts.

Detailed semantics are documented in `docs/domain/nutrition-target-model.md` and ADR-008.

### Health connections

Implemented:

- HealthConnection records owned by one Person;
- extensible provider keys for HealthKit, Health Connect, Garmin, Oura, Withings, Fitbit and future providers;
- stable connection keys that permit multiple paths/accounts for the same provider;
- device-bridge and cloud-API connection kinds;
- pending, active, paused, error and revoked lifecycle states;
- normalized granted permissions;
- optional provider account identity and non-secret provider metadata;
- opaque sync cursor plus last-attempt and last-success timestamps;
- explicit revocation timestamp;
- optional credential reference without storing raw access/refresh tokens in the domain table;
- database uniqueness and lifecycle validation;
- persistence and tests.

HealthConnection describes how health data enters NutriFlow.

Detailed semantics are documented in `docs/domain/health-connection-model.md` and ADR-009.

### Normalized health measurements

Implemented:

- person-scoped HealthMeasurement records;
- optional linkage to the HealthConnection used for ingestion;
- stable normalized metric keys, values and units;
- mutually exclusive point-in-time and interval temporal shapes;
- ingestion provider and underlying origin-provider provenance;
- source device, source application and source-kind metadata;
- ingestion and origin external identifiers;
- explicit source-chain metadata for bridge paths;
- versioned normalization semantics;
- deterministic deduplication keys;
- uniqueness of `(person_id, deduplication_key)` to prevent duplicate counting across ingestion paths;
- preservation of historical measurements when a HealthConnection is removed through `ON DELETE SET NULL`;
- database validation for temporal shape and non-empty deduplication identity;
- persistence and tests, including duplicate-path rejection.

Normalized health measurements are source observations. They are intentionally separate from provider payloads, specialized anthropometric history and derived DailyHealthState summaries.

Detailed semantics are documented in `docs/domain/health-measurement-model.md` and ADR-010.

### Daily health and nutrition state

Implemented:

- versioned DailyHealthState snapshots per Person and local calendar date;
- explicit timezone semantics for daily boundaries;
- typed health context for weight, weight trends, steps, energy, sleep, resting heart rate, HRV and training load;
- optional source-window timestamps and confidence score;
- versioned DailyNutritionState snapshots per Person and local calendar date;
- optional linkage to the NutritionTarget used for calculation;
- consumed, planned and remaining energy values;
- optional adherence and confidence scores;
- extensible DailyNutritionStateComponent records for nutrient-level consumed, planned and remaining values;
- negative remaining values so target overruns remain visible;
- calculation version, calculation-input metadata and computation timestamp for both state types;
- uniqueness by Person, state date and calculation version so algorithm evolution does not erase previous semantics;
- deterministic Person relationship ordering;
- database validation for ranges and component uniqueness;
- persistence and tests, including multiple calculation versions for one date.

Daily states are materialized derived data. They are recalculable from authoritative source history and must not replace HealthMeasurement, AnthropometricMeasurement, NutritionTarget or future meal/serving records.

Detailed semantics are documented in `docs/domain/daily-state-model.md` and ADR-011.

## Current database migration chain

The implemented schema includes migrations through DailyHealthState, DailyNutritionState and DailyNutritionStateComponent, following the Family/Person, profile/anthropometric, nutrition goal, nutrition constraint, food preference/adverse reaction, schedule, NutritionTarget, HealthConnection and HealthMeasurement migrations.

Alembic migrations are expected to be applied from an empty PostgreSQL database in CI and checked for model/schema drift.

## Next planned domain increments

Current sequence after the implemented foundation:

1. meal events, shared meals and individual servings;
2. adaptive planning and recommendation layers.

This list is directional. Each increment must be designed, documented, tested locally and validated in CI before integration into `main`.
