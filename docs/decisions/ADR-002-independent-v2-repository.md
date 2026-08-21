# ADR-002 — NutriFlow AI v2 is a standalone product

## Status

Accepted

## Decision

NutriFlow AI v2 is developed as a completely independent product.

It has its own repository, source tree, domain model, database schema, migrations, API contracts, user interface and product lifecycle.

No backward-compatibility requirements are assumed or required.

## Rationale

NutriFlow AI v2 is being designed around its own product requirements:

- Person as a core domain entity;
- Family context;
- individual and shared Meal Events;
- per-person Servings;
- health-data integrations;
- adaptive nutrition state;
- multilingual operation;
- responsive desktop and mobile experiences;
- Light, Dark and System themes.

Treating another implementation as an architectural ancestor would introduce constraints that are not required by the new product.

## Consequences

- database migrations begin from the NutriFlow AI v2 baseline;
- API contracts are designed solely for this product;
- no legacy compatibility layer is required;
- no previous database schema is imported;
- no previous source tree is considered authoritative;
- architectural decisions are made according to current product requirements.

Previous software may be examined independently for ideas when useful, in the same way any external reference might be examined, but it is not a dependency or migration source for NutriFlow AI v2.

