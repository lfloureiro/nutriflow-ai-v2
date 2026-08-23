# Meal discovery providers

NutriFlow separates **where meals can be discovered** from **whether a concrete meal can be nutritionally ranked**.

## Discovery preferences

A Family stores default discovery sources:

- `shared_recipes`
- `uber_eats`
- `glovo`
- `bolt_food`
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

## Delivery providers

Uber Eats, Glovo, and Bolt Food are separate providers even though all use the `delivery` practical channel. Recommendation requests carry `delivery_provider_keys`, so selecting one provider cannot leak offers from another.

A provider is considered **live** only when all three conditions are true:

1. required secrets are present through the configured secret store;
2. consumer discovery is explicitly enabled/approved for the deployment;
3. an executable `MealDeliveryDiscoveryAdapter` for that provider is registered.

Credentials alone never make an integration live. The capability endpoint reports missing credentials, missing approval/enablement, and missing executable adapter separately in its detail text.

Adapters are registered through `app.providers.registry`. Tests can register deterministic fake adapters; production will register only official/authorized implementations.

`POST /api/families/{family_id}/meal-discovery/providers/{provider_key}/sync` resolves the registered adapter, performs provider discovery, normalizes observations, ingests menu items and commercial offers, and commits only after the complete sync succeeds.

## External menu identity and nutrition evidence

A provider observation is normalized to a stable external dish identity. The FoodItem and its versioned nutrition evidence can be global/reusable, while availability and price remain Family/context-specific.

An external dish may exist with menu identity, price, and availability but no nutrition evidence. In that state it is deliberately **not eligible for nutrition ranking**.

Nutrition evidence is versioned as one of:

- `official`
- `provider`
- `estimated`

Estimated evidence requires an explicit confidence value. Provenance is retained in the composition snapshot and never silently replaced by a later estimate.

## Provider access policy

Uber Consumer Delivery is the intended Uber contract for consumer restaurant/menu discovery, but access is approval-controlled. Merchant/POS credentials must not be repurposed as consumer marketplace access.

The currently public Glovo and Bolt Food partner APIs are treated as merchant/POS/logistics integrations, not as proof of a general consumer marketplace discovery contract. Their consumer adapters remain disabled until an appropriate authorized contract is available.

Synthetic commercial fixtures may be used by automated tests, but the default development browser seed must not present them as live provider results.
