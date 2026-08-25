# ADR-035 — External data providers must allow zero-cost operation

## Status

Accepted.

## Context

NutriFlow uses external data for nutrition, restaurant discovery, menus, delivery availability,
and future health or commerce integrations. Some providers advertise a free usage allowance but
still require a billing-enabled account and can become chargeable automatically when that
allowance is exceeded.

The project must remain usable without recurring API charges.

## Decision

Normal NutriFlow operation must not depend on an external API that requires an active paid plan,
a mandatory billing account, or automatic pay-as-you-go overage.

Accepted provider classes are:

- open data or public APIs that are free to use within documented fair-use limits;
- provider free plans that require no payment method and stop, throttle, or fail when their free
  allowance is exhausted;
- self-hostable open-source services where NutriFlow can replace a public endpoint if usage grows.

A metered provider may be used only as optional enrichment when all of the following are true:

1. the application still works without it;
2. there is a free zero-dollar plan or allowance that does not require a payment method;
3. requests are cached and bounded;
4. the integration fails closed to a free fallback when the allowance is unavailable;
5. secrets are never committed to the repository.

Direct Google Maps Platform / Places API is not an operational dependency because it is a
pay-as-you-go platform. Its integration remains disabled by default.

For restaurant discovery, the baseline is OpenStreetMap data through Nominatim and Overpass,
subject to their usage policies. Apify Google Maps may be used only as optional free-plan
enrichment and must fall back to OpenStreetMap. Geoapify is an acceptable future hosted
alternative while its no-card free plan remains sufficient.

## Consequences

- Provider choice is constrained by cost model as well as data quality.
- Cache TTLs and request limits are part of provider correctness, not merely optimizations.
- A richer paid source cannot silently become required for recommendations.
- If a provider changes its pricing or free-plan conditions, its integration must be re-evaluated
  before continued use.
- Production scale may require self-hosting open data services rather than silently enabling paid
  APIs.
