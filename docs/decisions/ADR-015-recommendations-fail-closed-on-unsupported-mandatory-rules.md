# ADR-015: Recommendations fail closed on unsupported mandatory rules

## Status

Accepted

## Context

NutriFlow recommendation logic will eventually combine deterministic rules, heuristics and learned ranking.

Some inputs are preferences or optimization signals. Others are non-negotiable constraints such as allergies and mandatory clinician-defined nutrition rules.

A recommendation engine that silently ignores a mandatory rule merely because that rule is not yet implemented would create an unsafe architecture: adding a new constraint type could make recommendations less safe until every ranking implementation caught up.

## Decision

Recommendation processing is layered and mandatory constraints are evaluated before heuristic or learned ranking.

An active mandatory rule has only two acceptable outcomes:

1. the engine knows how to evaluate it and applies it; or
2. the engine stops the recommendation attempt explicitly.

The engine must not silently ignore an unsupported mandatory rule.

The initial implementation raises `UnsupportedMandatoryConstraintError` when it cannot evaluate an active mandatory NutritionConstraint safely.

Mandatory adverse reactions and supported mandatory food/nutrient constraints exclude matching candidates before scoring.

ML ranking, when added later, receives only candidates that have already passed mandatory-rule evaluation.

## Consequences

### Positive

- hard safety rules cannot be bypassed by heuristic or ML scores;
- unsupported mandatory semantics are visible during development and operation;
- adding a new mandatory constraint does not silently weaken existing safety;
- recommendation decisions remain explainable;
- testing can assert the safety boundary directly.

### Costs

- some recommendation requests may fail until a new mandatory constraint type is implemented;
- callers must surface or handle an explicit planning error;
- rule support must expand deliberately as the constraint vocabulary grows.

These costs are preferable to producing a recommendation whose compliance with a mandatory rule is unknown.

## Related decisions

- ADR-008: nutrition targets are derived and versioned;
- ADR-013: food and recipe composition is versioned;
- ADR-014: serving nutrition uses explicit composition and safe unit conversion.

## Future evolution

The rule engine may later expose richer typed diagnostics instead of a single exception class, but the fail-closed property must remain.

Schedule constraints, family-wide optimization, pantry constraints and future professional rules should each declare whether they are mandatory and how their evaluation is proven before ranking proceeds.
