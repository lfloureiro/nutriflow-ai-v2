# ADR-011: Daily states are derived, versioned and recalculable

## Status

Accepted

## Context

NutriFlow planning needs a compact view of a Person's current health context and nutrition progress.

The authoritative data is distributed across historical anthropometric records, normalized health measurements, nutrition targets and future meal/serving records.

Querying and aggregating all source records for every planning operation would make recommendation logic slower and harder to reason about.

At the same time, storing a daily summary without provenance or versioning could turn derived data into an accidental source of truth and make recalculation unsafe.

## Decision

NutriFlow will persist two distinct materialized daily summaries:

- `DailyHealthState` for health, body and activity context;
- `DailyNutritionState` for nutrition progress and remaining targets.

Both are derived records and are never authoritative replacements for their source data.

Each state is versioned by `calculation_version` and uniquely identified by the combination of Person, local state date and calculation version.

The explicit timezone defines the local calendar-day boundary.

Calculation-input metadata and computation timestamps are retained for explainability and reproducibility.

`DailyNutritionState` may reference the `NutritionTarget` used to derive the state. Nutrient progress is represented by extensible `DailyNutritionStateComponent` child records rather than a fixed column for every nutrient.

Remaining energy and nutrient values may be negative so that target overruns remain visible to planning logic.

## Consequences

### Positive

- planning logic can consume compact daily context;
- raw health and nutrition source history remains authoritative;
- algorithm changes can produce a new version without destroying previous state semantics;
- daily boundaries are explicit and timezone-aware;
- nutrient accounting can expand without adding a database column for every nutrient;
- negative remaining values preserve information about target overruns.

### Trade-offs

- derived state requires a future recomputation/invalidation strategy;
- multiple calculation versions can exist for the same date and Person;
- callers must deliberately choose the calculation version they consider current;
- source-lineage and freshness policies will need further implementation as the calculation pipeline evolves.

## Rejected alternatives

### Store only one mutable row per Person and date

Rejected because recalculating with new logic would erase the semantics of the previous calculation and make historical explanation difficult.

### Query raw source data for every recommendation

Rejected because it couples planning directly to ingestion/history tables and would repeatedly perform expensive aggregation work.

### Store all derived state as unstructured JSON

Rejected because core planning metrics need database-level validation and queryability. JSON remains appropriate for calculation-input metadata and future supplementary diagnostics.

### Clamp remaining values to zero

Rejected because exceeding a target is meaningful information. A negative remaining value communicates the size of that overrun.
