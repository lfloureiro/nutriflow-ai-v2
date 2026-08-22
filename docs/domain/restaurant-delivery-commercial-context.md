# Restaurant and delivery commercial context

NutriFlow needs restaurant and delivery candidates to carry durable commercial context without mixing provider state into the FoodItem/Recipe catalogue or weakening deterministic nutrition and safety rules.

This increment extends the persisted practical-availability layer with source opening windows and provider commercial offers.

## Source model

`MealCandidateAvailability` remains the Family-scoped identity for one concrete way to obtain a FoodItem or Recipe. Commercial planning uses source kinds `restaurant`, `delivery` and, where useful, `store`.

A commercial source can have zero or more `MealSourceOpeningWindow` rows and zero or more `MealCommercialOffer` rows.

The base source continues to own:

- Family scope;
- FoodItem or Recipe identity;
- source kind and stable source key;
- optional location;
- preparation/lead time;
- kitchen requirement;
- explicit operational availability;
- source provenance.

## Opening windows

`MealSourceOpeningWindow` stores recurring weekly local-time availability for a concrete source:

- weekday uses Python/PostgreSQL-style `0 = Monday` through `6 = Sunday`;
- local start and end time;
- explicit IANA timezone;
- optional local-date validity range;
- provider/source provenance and optional observation timestamp.

Window semantics are deterministic:

- start < end is a same-day half-open interval `[start, end)`;
- start > end crosses midnight and belongs to the weekday on which the interval starts;
- start == end represents a full local day for that weekday;
- overnight early-morning matching uses the previous local calendar date as the occurrence date;
- optional `valid_from`/`valid_until` apply to the occurrence date;
- an invalid/unknown timezone raises explicitly.

If a source has modeled opening windows and none match the planned instant, that source is closed. If a source has no opening-window rows, opening hours are unknown rather than assumed closed. This preserves the existing rule that missing practical metadata does not create a false exclusion.

## Commercial offers

`MealCommercialOffer` records one Family-scoped observed commercial offer for one concrete source:

- stable Family-scoped `offer_key`;
- provider key and optional display name;
- item price;
- three-character currency code;
- optional delivery fee;
- optional minimum order;
- explicit availability flag;
- optional absolute `valid_from`/`valid_until` interval;
- timezone-aware provider observation time;
- source/provider reference and notes.

Offer validity is half-open: `valid_from` is inclusive and `valid_until` is exclusive.

`total_known_price` is only `item_price + delivery_fee` when a delivery fee is known. Minimum order is retained as a basket-level condition and is not added to the item price.

The service does not convert currencies. Offers are ordered deterministically by candidate, currency, known total, provider and offer key. A EUR offer is never compared numerically with a USD offer as though they were the same unit.

## Planning integration

`build_commercial_planning_context()` evaluates commercial sources for one Family, candidate set and timezone-aware planned instant.

It returns:

- `CandidatePracticalProfile` records that can be passed to the existing practical recommendation layer;
- `CommercialOfferSnapshot` rows containing currently active provider offers.

Rules:

- candidate FoodItem/Recipe identities must already be persisted;
- Family-specific catalogue objects from another Family are rejected;
- duplicate candidate keys are rejected;
- source filters accept only commercial source kinds;
- a source must be operationally available and not explicitly closed at the planned instant;
- a modeled candidate with commercial source rows but no usable source becomes explicitly unavailable;
- a candidate with no modeled commercial source rows remains unknown and therefore yields no practical profile;
- active offer filtering does not determine source availability: an open restaurant/delivery source may remain practically available even when no currently valid price offer is known;
- provider offer Family mismatches and non-timezone-aware observation timestamps fail explicitly.

## Safety and ranking boundary

Commercial data is practical/commercial context, not a nutrition or food-safety authority.

The output can make a candidate practically unavailable before ranking, but it cannot make an otherwise unsafe candidate eligible. Any candidate that remains feasible still passes through the existing adverse-reaction, mandatory-constraint and nutrition logic.

Price does not currently change recommendation rank. This avoids prematurely mixing money, safety and nutrition objectives before a deliberate optimization policy is defined.

## Current limitations

This increment intentionally does not yet implement:

- provider API clients or credentials;
- live polling/webhooks;
- taxes, tips or service-charge calculation;
- basket composition and minimum-order satisfaction;
- coupons/promotions;
- dynamic delivery ETA beyond the existing preparation/lead-time field;
- geographic distance/routing;
- FX conversion;
- price-aware recommendation scoring;
- persisted order/cart lifecycle.

These can be added later without changing the authoritative FoodItem/Recipe nutrition model.

## Related decisions

- practical availability: `docs/domain/persisted-practical-availability.md`, ADR-023;
- practical recommendation context: `docs/domain/recommendation-practical-context.md`, ADR-019;
- pantry stock: `docs/domain/pantry-stock-shopping-requirements.md`, ADR-024;
- this commercial-context decision: ADR-025.
