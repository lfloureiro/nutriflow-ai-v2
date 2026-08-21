# Serving nutrition calculation

## Purpose

Serving nutrition is calculated from a specific versioned FoodCompositionSnapshot or RecipeCompositionSnapshot and the quantity represented by a Serving.

The calculation layer converts catalogue composition into the planned, served and consumed nutrition values stored on Serving and ServingNutritionComponent.

## Calculation model

Conceptually:

```text
composition value
x
serving quantity expressed in the composition reference unit
/
composition reference quantity
=
serving nutrition value
```

Example:

```text
Recipe composition: 2100 kcal per 1000 g
Planned serving:     350 g
Result:              735 kcal
```

The same calculation is performed independently for planned, served and consumed quantities.

## Versioned provenance

A calculated Serving records:

- either `food_composition_snapshot_id` or `recipe_composition_snapshot_id`;
- `nutrition_calculation_version`;
- `nutrition_source = catalog`;
- the calculated energy values on Serving;
- calculated nutrient values on ServingNutritionComponent.

Only one composition snapshot type may be linked to a Serving at a time.

The calculated values remain materialized on the Serving. If a catalogue record or composition link is later removed, the historical meal still retains the values that were actually used at the time.

## Safe unit conversion

Unit conversion is deliberately conservative.

The first calculation version supports explicit conversion within these dimensions:

- mass: `mg`, `g`, `kg`;
- volume: `ml`, `l`;
- any other unit only when the Serving unit and composition reference unit are exactly identical.

NutriFlow does not infer density.

For example, it will not automatically convert grams of milk to millilitres of milk, even if an approximate density might be known. Such a conversion requires explicit food-specific conversion data in a future domain layer.

Similarly, `piece`, `slice`, `cup`, `tablespoon` and other household units are not converted to mass or volume without an explicit conversion definition.

Unsafe or unsupported conversions fail rather than silently estimating.

## Catalogue consistency

The calculation service validates that the selected composition belongs to the same catalogue object as the Serving.

Examples:

- a FoodItem Serving may use a FoodCompositionSnapshot belonging to that FoodItem;
- a Recipe Serving may use a RecipeCompositionSnapshot belonging to that Recipe;
- a FoodItem Serving cannot be calculated from a Recipe composition;
- a Recipe Serving cannot be calculated from a FoodItem composition.

## Rounding

Calculations use Decimal arithmetic.

Materialized energy values are rounded to two decimal places and nutrient component values to four decimal places using explicit half-up rounding.

This avoids binary floating-point drift and aligns calculations with the precision of the persisted Serving schema.

## Recalculation

Serving nutrition is recalculable.

If a quantity changes or a newer catalogue composition is deliberately selected, the service recalculates the materialized energy and nutrient component values and records the composition snapshot and calculation version used.

A catalogue update must never silently mutate an existing Serving merely because a newer composition snapshot exists.

The caller must explicitly choose to recalculate.

## Future extensions

This foundation allows later support for:

- food-specific density conversions;
- household-unit conversion definitions;
- edible-portion and cooking-yield factors;
- automatic composition selection by effective date;
- recipe composition calculation directly from ingredient snapshots;
- provenance chains from Serving back to ingredient composition versions;
- recalculation of DailyNutritionState after serving changes.
