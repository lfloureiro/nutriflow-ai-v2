# ADR-025: Commercial source hours and offers are operational state

## Status

Accepted

## Context

NutriFlow already persists Family-scoped practical availability for home, pantry, restaurant, delivery and store sources. Restaurant and delivery planning also needs commercial facts such as opening hours, provider prices, delivery fees, minimum-order metadata and provider observation provenance.

These facts change independently from the nutritional identity of a FoodItem or Recipe. Storing them directly on catalogue composition would make nutritional history depend on volatile commercial data. Treating them as recommendation snapshots only would prevent reuse across planning runs and make source availability difficult to reason about.

## Decision

Commercial source context is persisted as operational state attached to `MealCandidateAvailability`.

Two records are introduced:

- `MealSourceOpeningWindow` for recurring weekly local-time source availability;
- `MealCommercialOffer` for one provider-observed monetary offer.

Opening-window decisions:

- weekday is `0 = Monday` through `6 = Sunday`;
- every window has an explicit IANA timezone;
- same-day windows use half-open `[start, end)` semantics;
- overnight windows belong to the weekday/date on which the interval begins;
- equal start/end means the source is open for the full local day;
- optional validity dates apply to the local occurrence date;
- no opening rows means opening hours are unknown, not closed.

Commercial-offer decisions:

- offers are Family-scoped and have a stable Family-scoped offer key;
- item price and a three-character currency are required;
- delivery fee and minimum order are optional;
- optional absolute validity uses inclusive `valid_from` and exclusive `valid_until`;
- provider observation time is required and timezone-aware;
- currencies are never converted or compared across currencies by this layer;
- minimum order is retained as metadata rather than treated as part of item price.

`build_commercial_planning_context()` adapts source state into the existing `CandidatePracticalProfile` interface while also returning active commercial-offer snapshots.

A candidate with modeled commercial sources but no usable source becomes practically unavailable. A candidate with no commercial source rows remains unknown. An open source can remain practically available even when no active price offer is known.

Commercial availability is evaluated before recommendation ranking. It cannot override adverse reactions, mandatory nutrition constraints or any other safety exclusion. Price is not yet part of recommendation scoring.

## Consequences

Benefits:

- catalogue nutrition remains stable and independent of volatile provider data;
- restaurant/delivery feasibility can use explicit opening hours;
- prices and provider provenance can be shown without introducing price ranking prematurely;
- provider synchronization has a durable persistence target;
- unknown hours/offers do not create false negatives;
- overnight opening-hour semantics are explicit and testable.

Costs:

- provider source state adds two operational tables;
- minimum-order feasibility still requires future basket-level logic;
- opening windows are weekly recurring windows rather than a full external-calendar model;
- real-time provider synchronization remains a later integration concern.

## Follow-up

Future increments may add provider connectors, live freshness policies, basket/order workflows, promotions, routing and deliberate price-aware multi-objective ranking. Those changes must preserve the deterministic safety boundary and must not infer currency conversion or provider availability silently.
