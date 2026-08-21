# ADR-002 — NutriFlow v2 uses an independent repository

## Status
Accepted

## Decision

NutriFlow AI v2 is developed in a new repository and directory rather than as an in-place rewrite of NutriFlow v1.

NutriFlow v1 remains available as a working reference and source of proven functionality.

## Rationale

The v2 domain model changes fundamental concepts including Person, Family, MealEvent, Serving and health/adaptive state. Building directly over the v1 structure would increase migration risk and preserve unnecessary legacy coupling.

## Migration approach

Every v1 component is explicitly classified as one of:

- reuse unchanged;
- port and adapt;
- migrate data only;
- replace;
- retire.

Reuse is based on continued correctness, not on minimising code changes.

## Consequences

- v1 can remain stable while v2 develops;
- v2 gets a clean schema and architecture;
- migration work must be tracked explicitly;
- duplicated functionality may temporarily exist during transition.
