# ADR-010: Health measurements normalize provenance before nutrition use

## Status

Accepted

## Context

NutriFlow AI v2 can receive health and activity information from multiple providers and through multiple paths.

The same underlying event may be visible through a direct provider API and through an aggregation platform such as Apple Health or Android Health Connect. Provider payloads also use different metric names, units, identifiers and timestamp structures.

Nutrition logic must not depend directly on provider-specific payload formats, and duplicate ingestion paths must not inflate activity, energy expenditure or other health signals.

## Decision

Provider data is normalized into a person-scoped `HealthMeasurement` model before it is used by nutrition logic.

HealthMeasurement records:

- use stable NutriFlow metric keys and normalized units;
- support explicit point and interval temporal shapes;
- preserve the provider through which data arrived;
- preserve the underlying origin provider when known;
- retain source device/app, external identifiers and source-chain metadata;
- record a normalization version;
- require a deterministic deduplication key.

The database enforces uniqueness of `(person_id, deduplication_key)`.

The deduplication key is produced by the ingestion/normalization layer from the strongest available identity. Stable origin identifiers are preferred. Deterministic fingerprints are a fallback when the upstream provider does not expose a reliable origin identifier.

A HealthConnection may be linked to a measurement, but measurements survive connection deletion by using `ON DELETE SET NULL`. Person deletion cascades to the person's health measurements.

## Consequences

Benefits:

- nutrition algorithms operate on one normalized representation;
- provider-specific API changes are isolated from the nutrition domain;
- cross-provider and bridge-path duplicate counting can be prevented;
- provenance remains explainable;
- normalization behavior can evolve with an explicit version;
- historical measurements remain available after a provider connection is removed.

Costs:

- ingestion adapters must calculate canonical metric/unit mappings and deduplication keys;
- not every provider exposes enough provenance for perfect identity matching;
- fallback fingerprints require careful metric-specific design;
- reconciliation between normalized health measurements and specialized domain histories such as anthropometric measurements requires a separate explicit projection policy.

## Boundaries

HealthMeasurement stores normalized observations, not raw provider credentials and not autonomous medical interpretation.

Future `DailyHealthState` and nutrition-planning logic consume normalized measurements and derived summaries rather than querying provider-specific payloads directly.
