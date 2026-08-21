# Daily health and nutrition state model

## Purpose

Daily state records are materialized, recalculable summaries used by planning and recommendation logic.

They exist so the application does not need to scan all raw health measurements, anthropometric history, nutrition targets and meal records every time it needs the current context for a Person.

Daily state is derived data. It is not the source of truth.

## Separation of concerns

NutriFlow keeps two daily state concepts separate:

- `DailyHealthState` summarizes health, activity and body context;
- `DailyNutritionState` summarizes nutrition progress against a target.

This separation prevents health observations from being mixed with nutrition accounting and allows each state to evolve independently.

## Versioning and recomputation

Both state types are identified by:

- `person_id`;
- `state_date`;
- `calculation_version`.

A Person may therefore have multiple state snapshots for the same date when calculation logic changes.

The unique key is intentionally `(person_id, state_date, calculation_version)` rather than only `(person_id, state_date)`.

Derived states may be recomputed from their authoritative inputs. The calculation version and calculation-input metadata make the result explainable and reproducible.

## Timezone semantics

`state_date` is a local calendar date interpreted in the explicit `timezone` stored on the state.

This is important because health and meal observations may be stored as timezone-aware timestamps while daily planning is calendar-day based.

A state must not infer its day boundary from the database server timezone.

## DailyHealthState

`DailyHealthState` is a compact summary of health and activity context that may influence planning.

Initial typed fields include:

- latest weight;
- 7-day weight trend;
- 28-day weight trend;
- steps;
- active energy;
- resting energy;
- estimated total expenditure;
- sleep duration;
- resting heart rate;
- HRV;
- training load;
- confidence score.

It also stores:

- `calculation_version`;
- `calculation_inputs`;
- optional source-window timestamps;
- `computed_at`.

The typed fields are intentionally limited to metrics with clear planning value. Raw provider-specific observations remain in `HealthMeasurement` and are not copied wholesale into DailyHealthState.

### Confidence

`confidence_score` is optional and constrained to the range 0..1.

It can reflect missing measurements, stale observations, weak source coverage or other uncertainty in the derived state.

The meaning of a particular confidence score belongs to the calculation version and must remain explainable.

## DailyNutritionState

`DailyNutritionState` summarizes progress for one Person and one local calendar day.

It may optionally reference the `NutritionTarget` used for the calculation.

Initial energy fields include:

- energy consumed;
- energy already planned;
- energy remaining to the lower target bound;
- energy remaining to the upper target bound.

It also stores:

- optional adherence score;
- optional confidence score;
- `calculation_version`;
- `calculation_inputs`;
- `computed_at`.

### Remaining values may be negative

Remaining energy and nutrient values are allowed to be negative.

A negative remaining value means the consumed plus planned amount has already exceeded that target boundary. Clamping remaining values to zero would hide useful planning information.

## DailyNutritionStateComponent

Nutrient accounting is extensible through child `DailyNutritionStateComponent` records rather than fixed columns for every nutrient.

Each component contains:

- target type;
- target key;
- consumed value;
- planned value;
- remaining minimum;
- remaining maximum;
- unit.

Examples include:

- protein in grams;
- fibre in grams;
- sodium in milligrams;
- carbohydrate in grams.

The combination `(daily_nutrition_state_id, target_type, target_key)` is unique.

Consumed and planned values are non-negative. Remaining values may be negative because they describe the distance to a target boundary rather than an amount consumed.

## Relationship to source data

The intended derivation flow is:

HealthConnection / HealthMeasurement / AnthropometricMeasurement
-> DailyHealthState

NutritionGoal / NutritionTarget / future MealEvent and Serving records
-> DailyNutritionState

Daily state records must not replace those source records.

Deleting or rebuilding derived state must not destroy authoritative history.

## Relationship to planning

Planning and recommendation logic should normally consume daily state rather than repeatedly aggregating every source table.

The intended loop is:

raw observations and planned/actual intake
-> normalized source records
-> daily derived state
-> planning and recommendation
-> new planned/actual intake
-> next recalculation

This keeps recommendation logic fast while preserving traceability back to authoritative inputs.

## Future evolution

Future increments may add:

- explicit state-generation services;
- freshness/staleness policy;
- richer confidence diagnostics;
- source-record lineage identifiers;
- background recomputation;
- caching or event-driven invalidation;
- additional typed health metrics only when they have a justified planning use case.

Those capabilities should preserve the core rule that daily state is derived, versioned and recalculable.
