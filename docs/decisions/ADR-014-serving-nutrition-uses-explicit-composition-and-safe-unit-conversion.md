# ADR-014: Serving nutrition uses explicit composition snapshots and safe unit conversion

## Status

Accepted.

## Context

NutriFlow must turn a catalogue food or recipe composition into person-specific Serving nutrition.

The same food may have multiple composition snapshots over time. Serving quantities may also use units that differ from the composition reference unit.

A naive implementation could silently select the newest composition or make approximate conversions between incompatible units. Either behaviour would make historical intake difficult to explain and could introduce hidden nutrition errors.

## Decision

Serving nutrition calculation must use one explicitly selected FoodCompositionSnapshot or RecipeCompositionSnapshot.

The Serving persists the selected composition snapshot reference and a nutrition-calculation version in addition to the materialized calculated values.

The calculation service scales energy and nutrient values independently for planned, served and consumed quantities.

Unit conversion is conservative:

- mass conversion is supported only between `mg`, `g` and `kg`;
- volume conversion is supported only between `ml` and `l`;
- other units are valid only when source and target units are exactly equal;
- cross-dimension conversion is rejected;
- no density or household-unit conversion is inferred.

The service validates that the composition snapshot belongs to the same FoodItem or Recipe represented by the Serving.

## Consequences

Positive consequences:

- historical Serving calculations remain explainable;
- catalogue corrections do not silently change previous intake;
- unsafe unit assumptions fail visibly;
- planned, served and consumed nutrition use the same calculation semantics;
- later DailyNutritionState recalculation can identify the exact source composition.

Trade-offs:

- some common kitchen conversions require explicit future conversion data;
- callers must deliberately choose a composition snapshot;
- calculated Serving values are materialized and therefore must be recalculated explicitly when inputs change.

## Rejected alternatives

### Always use the latest catalogue composition

Rejected because historical meals would become dependent on current catalogue state and could change meaning after a label or recipe correction.

### Automatically convert between mass and volume

Rejected because density is food-specific and context-dependent. A generic conversion would create false precision.

### Store only the composition snapshot and calculate values on every read

Rejected because Serving is authoritative historical meal data used repeatedly by daily-state and planning calculations. Materialized values make the historical result stable and efficient while the composition link preserves provenance.
