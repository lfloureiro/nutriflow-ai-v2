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

For DailyNutritionState, rerunning the same calculation version updates that derived snapshot in place. Changing the calculation version creates a separate snapshot with different algorithm semantics.

## Timezone semantics

`state_date` is a local calendar date interpreted in the explicit `timezone` stored on the state.

This is important because health and meal observations may be stored as timezone-aware timestamps while daily planning is calendar-day based.

A state must not infer its day boundary from the database server timezone.

The Serving-based DailyNutritionState recalculation service builds explicit local midnight-to-midnight boundaries from the supplied IANA timezone.

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

### Serving-derived recalculation

Persisted Serving history is now the authoritative source for DailyNutritionState meal accounting.

Cancelled/replaced MealEvents, skipped/replaced MealParticipants and skipped/replaced Servings are excluded.

A realized Serving contributes consumed values and no longer contributes its old planned values. For a non-realized Serving already in `served` state, served values are preferred over planned values when available. Other included non-realized Servings contribute planned values.

This prevents the same portion from being counted both as consumed and as future planned intake.

When a NutritionTarget is supplied, it must belong to the same Person and be valid on the state date. Nutrient values are converted into the target component unit only through explicit safe conversions. Unsafe required conversions cause recalculation to fail rather than silently undercounting intake.

Detailed aggregation semantics are documented in `docs/domain/daily-nutrition-recalculation.md` and ADR-018.

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

The current recalculation service materializes nutrient components represented by the selected NutritionTarget. A point-only target (`value_target` without minimum/maximum) is represented by equal remaining minimum and maximum values.

## Relationship to source data

The derivation flow is:

HealthConnection / HealthMeasurement / AnthropometricMeasurement
-> DailyHealthState

NutritionGoal / NutritionTarget + MealEvent / MealParticipant / Serving
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

- automatic target selection policy;
- adherence and confidence calculations;
- freshness/staleness policy;
- background/event-driven recomputation after meal writes;
- caching or invalidation;
- richer source-lineage diagnostics;
- additional typed health metrics only when they have a justified planning use case.

Those capabilities should preserve the core rule that daily state is derived, versioned and recalculable.
