# Nutrition Target Domain Model

## Purpose

`NutritionTarget` represents a derived nutrition recommendation snapshot for one Person over a defined period of time.

It is intentionally separate from:

- `NutritionGoal`, which describes what the person is trying to achieve;
- `NutritionConstraint`, which describes rules that recommendations must respect;
- `DailyNutritionState`, which will later describe what has been consumed, planned and remains available on a particular day.

Nutrition targets are calculated outputs. They are not permanent mutable fields on `Person`.

## Versioned snapshots

A recalculation creates a new `NutritionTarget` rather than overwriting the previous calculation.

This preserves the ability to answer questions such as:

- what target was active on a given date;
- why the target changed;
- which calculation version produced it;
- which goal was associated with it;
- which inputs were used;
- whether observed results later justified another recalculation.

Typical status values include:

- `active`;
- `superseded`;
- `expired`.

Status values remain application-level vocabulary rather than database enums so the workflow can evolve without schema churn.

## NutritionTarget

Core fields include:

- `person_id`;
- optional `nutrition_goal_id`;
- `valid_from`;
- optional `valid_until`;
- `estimated_bmr_kcal`;
- `bmr_method`;
- `estimated_tdee_kcal`;
- `tdee_method`;
- `energy_min_kcal`;
- `energy_max_kcal`;
- `calculation_version`;
- `calculation_inputs`;
- `status`;
- `source`;
- `notes`;
- timestamps.

The database validates positive BMR, TDEE and energy values, valid energy ranges and valid date ranges.

## Calculation provenance

`calculation_version` identifies the calculation logic that produced the snapshot.

`calculation_inputs` stores explainability context required to reconstruct why the result exists. It may contain values such as:

- anthropometric input values;
- activity source or classification;
- goal type;
- relevant measurement identifiers or normalized values;
- other calculation parameters.

The JSON input snapshot is supporting provenance, not a replacement for normalized source entities.

Canonical health, anthropometric and goal data remains in its own domain tables.

## Energy calculation chain

A typical calculation chain is:

Person profile and measurements
-> BMR estimate
-> baseline or observed activity
-> estimated TDEE
-> active NutritionGoal adjustment
-> NutritionConstraint application
-> energy target range
-> nutrient target components

Each significant algorithm change should use a new `calculation_version`.

## NutritionTargetComponent

Nutrient recommendations are modeled as child components rather than fixed columns on `NutritionTarget`.

This avoids hard-coding only today's known nutrients and allows the target system to expand without repeatedly changing the parent table.

Each component contains:

- `nutrition_target_id`;
- `target_type`;
- `target_key`;
- optional `value_min`;
- optional `value_max`;
- optional `value_target`;
- `unit`;
- timestamps.

Examples:

- protein: 130-170 g/day;
- fibre: target 35 g/day;
- sodium: maximum 2000 mg/day;
- carbohydrate: 180-240 g/day.

At least one target value must be present for each component.

A target snapshot cannot contain duplicate `(target_type, target_key)` components.

## Constraints versus targets

A constraint and a target are not interchangeable.

Example:

A clinician may define a mandatory sodium maximum of 2000 mg/day as a `NutritionConstraint`.

The calculation layer may then produce a sodium component of 1800-2000 mg/day inside a `NutritionTarget`.

The constraint is an input rule. The target is a derived output that already respects that rule.

## Historical behaviour

When a target is recalculated:

1. the current target is retained;
2. it can be marked `superseded` and assigned `valid_until`;
3. a new target is created with a later `valid_from`;
4. the new target records its calculation version and inputs.

Historical snapshots should not be rewritten merely because newer measurements become available.

## Relationship to future daily state

`NutritionTarget` describes the recommendation baseline for a period.

Future `DailyNutritionState` will combine the applicable target with day-specific information such as:

- meals already consumed;
- meals already planned;
- activity context;
- remaining energy;
- remaining protein or other nutrient targets;
- adherence and confidence indicators.

This separation keeps long-lived target history independent from recalculable daily state.
