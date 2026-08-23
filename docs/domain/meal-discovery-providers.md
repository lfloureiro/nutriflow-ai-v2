# Meal discovery providers

NutriFlow separates **where meals can be discovered** from **whether a concrete meal can be nutritionally ranked**.

## Discovery preferences

A Family stores default discovery sources:

- `shared_recipes`
- `uber_eats`
- `glovo`
- `restaurants`

A Person inherits the Family defaults unless an explicit override is stored on the Person profile. Delivery address and restaurant area follow the same inheritance model.

For shared recommendations, the UI uses only sources accepted by every selected Person.

## Shared recipes

Recipes with `Recipe.family_id = NULL` are global catalogue recipes. They are visible to every Family and are read-only from Family-scoped editing endpoints. Ratings and recommendation feedback remain Person/Family-specific because preferences refer to the stable `recipe_key`, not recipe ownership.

Family-owned recipes remain private/editable and are visible only to that Family.

## Live restaurant discovery

`GET /api/families/{family_id}/restaurant-discovery` performs an explicit user-triggered restaurant-area lookup.

The initial provider is OpenStreetMap:

1. Nominatim resolves the configured/free-text area to a bounding box.
2. Overpass finds `restaurant`, `fast_food`, and `food_court` POIs in that bounding box.
3. NutriFlow returns observed place metadata with provider identity and attribution.
4. Results are cached for six hours by default.

Provider endpoints, timeout, cache duration, result limit, and User-Agent are application settings so production deployments can switch to a commercial or self-hosted provider without changing the domain contract.

The public OpenStreetMap services are intended only for moderate, directly user-triggered use. Production scale should use a suitable commercial or self-hosted service.

## Restaurant metadata is not meal nutrition

A discovered restaurant is **not** automatically a recommendation candidate.

Restaurant name, cuisine, coordinates, website, phone, and opening hours are discovery metadata. They do not provide enough evidence to claim calories, macros, allergens, sodium, or portion size for a meal.

A restaurant dish becomes nutritionally rankable only after NutriFlow has a concrete menu-item identity plus nutrition evidence or an explicitly versioned estimate with provenance/confidence. Estimated nutrition must never silently replace provider nutrition and must not override mandatory safety exclusions.

## Uber Eats and Glovo

Uber Eats and Glovo are separate providers even though both use the `delivery` practical channel. Recommendation requests carry `delivery_provider_keys`, so selecting one provider cannot leak offers from the other.

Live provider adapters must use official/authorized integrations and preserve provider provenance. Synthetic commercial fixtures may be used by automated tests, but the default development browser seed must not present them as live results.
