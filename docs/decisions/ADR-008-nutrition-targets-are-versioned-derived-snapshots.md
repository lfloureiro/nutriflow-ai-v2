# ADR-008: Nutrition targets are versioned derived snapshots

## Status

Accepted

## Context

NutriFlow AI must adapt nutrition recommendations as goals, body measurements, observed activity and other inputs change.

Storing calorie and nutrient targets directly on `Person` would erase the history of previous recommendations and make it difficult to explain why a target changed.

A single fixed nutrition-target schema containing one column for every nutrient would also make the model brittle as new nutrients and recommendation types are introduced.

## Decision

Nutrition recommendations are represented as versioned `NutritionTarget` snapshots linked to a Person.

Each snapshot has an explicit validity period, calculation version, calculation-input provenance and optional relationship to the NutritionGoal that informed it.

Energy-level outputs such as BMR, TDEE and target energy range belong to the snapshot.

Individual nutrient recommendations are represented as extensible `NutritionTargetComponent` child records using a target type, stable target key, values and unit.

A recalculation creates a new snapshot rather than overwriting historical values.

`NutritionConstraint` remains a separate input-rule concept. A target is a derived result that should already respect applicable constraints.

`DailyNutritionState` remains a separate future derived-state concept for day-specific consumed, planned and remaining nutrition values.

## Consequences

Benefits:

- historical recommendations remain auditable;
- target changes can be explained from calculation version and inputs;
- observed outcomes can later be compared with the target that was active at the time;
- nutrient coverage can expand without adding fixed parent-table columns;
- goals, constraints, targets and daily state retain clear domain boundaries.

Costs:

- target recalculation creates additional records;
- application logic must identify the applicable snapshot for a date;
- calculation-input JSON must not become a substitute for normalized source data;
- lifecycle rules must eventually manage active, superseded and expired snapshots consistently.
