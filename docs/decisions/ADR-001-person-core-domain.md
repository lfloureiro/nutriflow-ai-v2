# ADR-001 — Person is the core domain entity

## Status
Accepted

## Decision

NutriFlow AI v2 is person-centric. `Person` is the primary domain entity for nutrition planning, health data, goals, constraints and outcomes.

`Family` provides shared context and resources but does not replace person-specific nutrition state.

## Rationale

People in the same family have different:

- calorie and nutrient requirements;
- body measurements;
- goals;
- schedules;
- activity/training;
- allergies and restrictions;
- preferences;
- health data;
- observed outcomes.

A household-centric model cannot represent these differences cleanly without accumulating exceptions.

## Consequences

- health connections belong to Person;
- goals and constraints belong to Person;
- DailyNutritionState and DailyHealthState are person-specific;
- family meals use participants and per-person Servings;
- shared household data remains attached to Family/Household context.
