# External meal sources

Status: active design contract for `feature/family-catalog-and-profile-editing`.

## Purpose

NutriFlow must distinguish three different questions:

1. **Which restaurants are worth considering?**
2. **Which concrete dishes are currently available?**
3. **Which of those dishes have enough nutritional evidence to be ranked for a Person or Family?**

A restaurant rating is not nutritional evidence, and a delivery listing is not automatically a safe nutrition candidate.

## Restaurant discovery

Restaurant discovery uses this order:

```text
Google Places when configured
-> OpenStreetMap fallback
```

Google Places contributes quality/reputation signals such as rating, review count, price level, restaurant type and service flags. OpenStreetMap remains a no-key fallback and is not treated as equivalent evidence for quality ranking.

Ranking currently prefers full-service restaurants over food courts and fast-food establishments, then uses a Bayesian quality score that combines rating with review volume. Duplicate chain locations are collapsed by normalized name and, when available, by a non-generic official website host.

TheFork, social networks and review aggregators may be useful references for a human or a future approved integration, but they are not used as automated identity keys and NutriFlow does not scrape them.

## Delivery menus

Supported source keys are:

```text
uber_eats
glovo
bolt_food
```

Selection by a Family does not imply live access. A provider is live only when all required conditions hold:

```text
credentials present
+ consumer discovery access enabled/approved
+ executable adapter registered
```

Uber Consumer Delivery is the intended official consumer integration when access is approved. The currently documented public Glovo and Bolt Food APIs are primarily merchant/POS integrations; NutriFlow must not pretend they provide general consumer marketplace discovery when they do not.

No provider marketplace is scraped as a substitute for an approved contract.

## Persisted menu catalogue

Every observed external menu item is normalized into the existing catalogue/availability/offer model.

External dishes are **Family-scoped**, not global shared FoodItems. The same provider/merchant/item observed by two Families produces two distinct catalogue keys. This prevents a dish synchronized for one Family from leaking into another Family's planning bootstrap.

The delivery-menu screen reads persisted current offers, not only the response of the most recent sync. Reloading the Web app therefore preserves the Family's observed catalogue while the offer remains valid and available.

Persisted cards expose:

- provider and merchant;
- dish name and description;
- item price;
- delivery fee and minimum order when observed;
- observation time;
- source reference;
- energy and evidence state when available.

Expired or unavailable offers are not returned as current delivery-menu items.

## Nutritional evidence

External menu nutrition supports three evidence levels:

```text
official
provider
estimated
```

`estimated` evidence requires an explicit confidence value. Missing nutrition remains missing; it is not silently invented.

A concrete dish enters nutrition ranking only when a persisted composition snapshot exists with usable energy evidence. The recommendation engine may still expose a restaurant separately for discovery, but it must not assign restaurant-level calories or treat a place rating as a meal composition.

This contract intentionally allows future approved menu extractors or curated imports to reuse the same pipeline without changing recommendation semantics. They must still provide source/provenance and, for estimates, confidence.

## Security and isolation

Commercial offers and candidate availability are Family-scoped. External FoodItems are also Family-scoped even when the provider catalogue itself is public. Production authorization remains a separate concern; Family UUID context is not yet a production authentication boundary.
