# DailyNutritionState recalculation

## Purpose

`DailyNutritionState` is derived planning state. `MealEvent`, `MealParticipant` and `Serving` remain the authoritative meal history.

The recalculation service rebuilds one Person's nutrition state for one local calendar date from persisted Serving records and, when supplied, one applicable `NutritionTarget`.

## Local-day boundary

The caller provides:

- `state_date`;
- an IANA timezone such as `Europe/Lisbon`.

The service builds local midnight-to-midnight boundaries in that timezone and queries timezone-aware `MealEvent.scheduled_at` values against those boundaries.

This means an event close to UTC midnight belongs to the local date seen by the Person rather than to the database server's calendar date.

Unknown timezones are rejected.

## Authoritative inclusion rules

Servings are selected through the Person's `MealParticipant` records for the requested local day.

The following records do not contribute:

- MealEvents with status `cancelled` or `replaced`;
- MealParticipants with status `skipped` or `replaced`;
- Servings with status `skipped` or `replaced`.

This prevents abandoned plans and superseded records from continuing to affect current nutrition state.

## Planned versus consumed precedence

A Serving is treated as realized when it is `consumed` or `partial`, has consumed energy, or contains a consumed nutrient value.

For a realized Serving:

- consumed energy/nutrients contribute to consumed totals;
- planned and served values no longer contribute to planned totals.

For a non-realized Serving with status `served`:

- served energy/nutrient values are used as the best current estimate of future intake when present;
- planned values are the fallback when a served value is missing.

For other non-realized included Servings:

- planned energy/nutrient values contribute to planned totals.

This prevents one Serving from being counted simultaneously as both consumed and still planned.

## NutritionTarget use

A `NutritionTarget` is optional.

When provided, it must:

- belong to the same Person;
- be persisted;
- be valid on `state_date`.

The service does not silently choose between overlapping target versions. Target selection remains an explicit upstream decision.

Energy remaining values are calculated as:

`target bound - (consumed + planned)`

Negative remaining values are preserved.

For nutrient components, only `NutritionTargetComponent` records with `target_type="nutrient"` are materialized in `DailyNutritionStateComponent`.

If a nutrient target has only `value_target` and no minimum/maximum range, that point target is represented by equal `remaining_min` and `remaining_max` values.

Without a NutritionTarget, energy consumed/planned totals are still derived, but target-relative remaining values and nutrient target components are not fabricated.

## Unit conversion

Serving nutrient values are converted into the unit defined by the matching NutritionTargetComponent.

The conversion policy is the same conservative policy used by Serving nutrition calculation:

- mass: `mg`, `g`, `kg`;
- volume: `ml`, `l`;
- exact same-unit values;
- no implicit mass/volume conversion;
- no inferred density.

An incompatible required conversion aborts recalculation rather than silently undercounting the nutrient.

## Versioning and recomputation

The identity remains:

`(person_id, state_date, calculation_version)`

Re-running the same calculation version updates the existing derived state in place, including its existing component rows.

Changing `calculation_version` creates a separate state version so older algorithm semantics remain available.

The service records calculation metadata including:

- local source window;
- included Serving IDs;
- Serving count;
- NutritionTarget ID when present;
- aggregation policy.

`computed_at` is refreshed on each recomputation.

## Current exclusions

This increment does not yet calculate:

- adherence score;
- confidence score;
- automatic target selection;
- event-driven/background invalidation;
- state refresh automatically after every meal write;
- nutrients that are not represented by the selected NutritionTarget.

Those can be layered on without changing the rule that authoritative Serving history is the source of nutrition accounting.
