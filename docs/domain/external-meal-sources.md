# External meal sources

Status: active design contract for `feature/automatic-meal-intelligence`.

## Purpose

NutriFlow distinguishes three different questions:

1. **Which restaurants are worth considering?**
2. **Which concrete dishes are currently available?**
3. **Which of those dishes have enough nutritional evidence to be ranked for a Person or Family?**

The recommendation target is a concrete meal or dish. A restaurant name by itself is discovery context, not a complete meal recommendation.

## Canonical restaurant discovery

Restaurant discovery uses this order:

```text
Google Places when configured
-> OpenStreetMap fallback when Google is not the active source
```

Google Places contributes identity and quality/reputation signals such as rating, review count, price level, restaurant type, website and service flags. OpenStreetMap remains a no-key fallback and is not treated as equivalent quality evidence.

For recommendation-time menu synchronization, NutriFlow does not mix both sources silently. If Google Places is configured, the restaurant-menu workflow requires Google results rather than accepting an OpenStreetMap fallback under the same recommendation run. This keeps the Restaurant screen and recommendation engine on one canonical source contract.

Ranking prefers full-service restaurants over food courts and fast-food establishments, then uses a quality score that combines rating with review volume. Duplicate chain locations are collapsed by normalized name and, when available, by a non-generic official website host.

## Official restaurant websites and menus

For a discovered restaurant with an official website, NutriFlow may crawl the public restaurant site to locate its own menu/ementa. This is distinct from scraping a delivery marketplace or review aggregator.

The crawler:

- accepts public HTTP(S) restaurant websites only;
- rejects localhost, private/non-global IP targets and unresolved hosts;
- observes `robots.txt`;
- limits response size, request time, scanned pages and extracted items;
- follows same-host links associated with menus/ementas and PDFs;
- extracts structured JSON-LD `MenuItem`/`Product` data when present;
- supports common HTML/microdata menu blocks;
- extracts text-based PDF menus;
- preserves the exact source page for every observed dish;
- deduplicates repeated menu items.

The crawler does not use OCR in this backend flow. Image-only menus can therefore remain unreadable until a future explicit image-menu pipeline is added.

## Restaurant dishes as recommendation candidates

A synchronized menu dish is normalized into the existing Family-scoped `FoodItem + availability + commercial offer` model.

For restaurant website observations:

```text
source_kind = restaurant
provider_key = restaurant_website
provider_name = actual restaurant name
location = configured/searched restaurant area
```

The recommendation engine consumes those dish candidates. It no longer treats the separately discovered restaurant name as the meal to recommend.

Commercial dishes remain real fixed servings. NutriFlow evaluates whether one observed serving fits the person's energy budget instead of fabricating `1.25` or `1.5` restaurant portions.

## Nutritional evidence for restaurant dishes

Menu nutrition can have several evidence levels.

If the official menu publishes kcal, that is retained as direct menu evidence. If kcal are not published, NutriFlow may estimate energy only when a sufficiently strong matching NutriFlow Recipe has usable non-estimated nutrition evidence. The matched Recipe reference and confidence are retained with the estimate.

A weak textual resemblance is not enough to assign calories. A dish without usable nutrition can remain visible in the menu but does not enter nutrition ranking.

Restaurant rating, review count, cuisine and price are ranking/context signals; none of them is nutritional evidence.

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

No delivery marketplace is scraped as a substitute for an approved consumer contract. TheFork, social networks and review aggregators are likewise not scraped as menu providers.

## Persisted external catalogue

Every observed external menu item is Family-scoped. The same provider/merchant/item observed by two Families produces two distinct catalogue keys, preventing a dish synchronized for one Family from leaking into another Family's planning bootstrap.

Persisted current offers expose, where known:

- restaurant/provider and merchant identity;
- dish name and description;
- item price and currency;
- delivery fee/minimum order for delivery sources;
- observation time and validity window;
- exact source reference;
- energy and evidence state.

Expired or unavailable offers are not returned as current options.

## Source isolation during recommendation

The user's selected source constrains the candidate set:

- `restaurant` accepts restaurant website offers;
- `uber_eats`, `glovo` and `bolt_food` accept only their own delivery offers;
- `cooked` accepts Recipe candidates.

A persisted commercial dish is therefore not allowed into a recommendation merely because its generic food kind is `dish`.

## Security and isolation

Commercial offers, candidate availability and external FoodItems are Family-scoped. Website fetching has SSRF protections as described above. Production authorization remains a separate concern; Family UUID context is not yet a production authentication boundary.
