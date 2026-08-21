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

Nutrition targets are derived outputs. They remain separate from NutritionGoal, NutritionConstraint and future DailyNutritionState concepts.

Detailed semantics are documented in `docs/domain/nutrition-target-model.md` and ADR-008.

## Current database migration chain

The implemented schema includes migrations through NutritionTarget and NutritionTargetComponent, following the Family/Person, profile/anthropometric, nutrition goal, nutrition constraint, food preference/adverse reaction and schedule migrations.

Alembic migrations are expected to be applied from an empty PostgreSQL database in CI and checked for model/schema drift.

## Next planned domain increments

Current sequence after the implemented foundation:

1. health-provider connections;
2. normalized health measurements with provenance and deduplication;
3. DailyHealthState and DailyNutritionState;
4. meal events, shared meals and individual servings;
5. adaptive planning and recommendation layers.

This list is directional. Each increment must be designed, documented, tested locally and validated in CI before integration into `main`.
