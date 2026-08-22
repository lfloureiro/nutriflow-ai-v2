# Pantry stock and shopping requirements

NutriFlow needs pantry-aware planning to distinguish a meal that is generally obtainable from one that the household can actually prepare from the quantities currently on hand. This increment adds quantity-aware Family pantry stock, expiry handling, recipe ingredient sufficiency and deterministic shopping requirements.

## PantryStockLot

`PantryStockLot` is a current operational stock record for one Family and one FoodItem.

Each lot records:

- Family ownership;
- FoodItem identity;
- a Family-scoped stable `stock_key`;
- currently available quantity and unit;
- optional storage location;
- optional expiry instant;
- observation instant;
- explicit availability state;
- source provenance, source reference and notes.

The quantity must be positive. An exhausted or unavailable lot should be marked unavailable or replaced by a newer stock observation rather than stored with a zero or negative quantity.

Pantry stock is operational state rather than immutable meal history. Deleting the Family or FoodItem therefore cascades to its pantry lots. Historical Serving and recommendation evidence remain protected independently by their existing snapshots and provenance.

## Expiry semantics

Pantry evaluation requires a timezone-aware `as_of` instant.

A lot contributes only when:

- it belongs to the requested Family;
- it belongs to the requested FoodItem;
- `is_available` is true; and
- `expires_at` is null or strictly later than `as_of`.

A lot expiring exactly at `as_of` is treated as expired.

## Quantity and unit safety

Pantry quantities reuse the same conservative quantity conversion rules as serving nutrition:

- mass: `mg`, `g`, `kg`;
- volume: `ml`, `l`;
- exact same-unit values.

No density or cross-dimension inference is performed. If a required quantity and an available stock quantity cannot be safely compared, pantry sufficiency fails explicitly with `PantryUnitConversionError` rather than assuming the ingredient is present.

## FoodItem stock assessment

`assess_food_pantry_stock()` compares one required FoodItem quantity against all active, non-expired pantry lots for the Family.

The result records:

- required quantity;
- total safely convertible available quantity;
- missing quantity, never below zero;
- unit used for the comparison;
- stock-lot IDs that contributed to the total.

The result is sufficient only when missing quantity is zero.

## Recipe ingredient sufficiency

`evaluate_recipe_pantry_sufficiency()` evaluates one persisted Recipe for a positive batch multiplier.

Rules are deterministic:

- the Recipe must be global or belong to the requested Family;
- every ingredient FoodItem must be global or belong to the requested Family;
- ingredient quantities are multiplied by the batch multiplier;
- repeated RecipeIngredient rows for the same FoodItem are combined before stock comparison;
- repeated ingredient units must be safely convertible;
- each aggregated ingredient is compared against current non-expired pantry stock.

The result contains one `FoodPantryAssessment` per aggregated ingredient.

## Shopping requirements

Every ingredient with a positive missing quantity becomes a `ShoppingRequirement` containing:

- FoodItem identity;
- catalogue key and display name;
- exact missing quantity;
- unit.

Shopping requirements are deterministic calculation results in this increment. They are not yet persisted shopping-list rows and do not represent a purchase order.

## Recommendation integration

`build_pantry_stock_practical_profiles()` converts current pantry sufficiency into the existing `CandidatePracticalProfile` interface.

For FoodItem candidates, the recommended quantity is checked directly against stock.

For Recipe candidates, the candidate quantity is scaled against the Recipe `yield_quantity` and `yield_unit`. Recipes without usable yield metadata cannot be evaluated as pantry candidates and fail explicitly rather than receiving an optimistic availability result.

The resulting practical profile only contributes explicit `is_available`. It does not infer preparation time, kitchen requirements or location. Those remain separate practical-source concerns.

Pantry availability still precedes the existing hard-rule-first recommendation engine. It cannot override allergies, adverse reactions or mandatory NutritionConstraint rules.

Restaurant/delivery/store prices and opening hours are now modeled separately in `docs/domain/restaurant-delivery-commercial-context.md`; they do not change pantry stock semantics.

## Current limitations

This increment intentionally does not yet implement:

- reservation or decrement of pantry stock when a meal is planned;
- pantry consumption history or stock-movement ledger;
- persisted shopping lists/orders;
- package-size optimization or price comparison;
- substitutions between different FoodItems;
- density-based conversions;
- real-time retailer inventory.

These can be layered on the quantity-safe pantry assessment without changing recommendation safety semantics.

## Next steps

1. persist shopping-list and requirement lifecycle when API/UI workflows need durable shopping state;
2. expose pantry/shopping operations through coherent API/UI vertical slices;
3. add stock movements/reservations if concurrent meal planning requires them;
4. add package-size optimization, retailer inventory and price comparison only with explicit provider/freshness rules.
