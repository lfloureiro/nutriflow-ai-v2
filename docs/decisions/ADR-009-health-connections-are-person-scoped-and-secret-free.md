# ADR-009: Health connections are person-scoped and secret-free

## Status

Accepted

## Context

NutriFlow AI v2 will consume health and activity data from device platforms and provider APIs such as Apple HealthKit, Android Health Connect, Garmin, Oura, Withings and Fitbit.

A Family can share meal-planning context, but health permissions and health-provider accounts belong to individual people. Provider integrations also require operational state such as permissions, sync cursors and last-successful-sync timestamps.

Some integrations use server-held credentials while others are device mediated. Storing raw access or refresh tokens in the domain table would unnecessarily couple health-domain persistence to secret storage and increase the impact of a database exposure.

## Decision

Health-provider connections are modeled as `HealthConnection` records owned by one Person.

Each connection records:

- provider identity;
- a NutriFlow-level connection key;
- connection kind;
- lifecycle status;
- normalized granted permissions;
- optional provider account identifier;
- optional non-secret provider metadata;
- sync cursor and sync timestamps;
- revocation timestamp;
- an optional opaque credential reference.

Raw access tokens, refresh tokens and API secrets are not stored in the HealthConnection row.

When server-held credentials are required, `credential_reference` points to an external secret-management mechanism.

Provider-specific integration logic is implemented behind adapters rather than embedded in the Person or HealthConnection model.

## Consequences

Benefits:

- health authorization remains person-scoped;
- Family membership does not imply access to another person's health integrations;
- provider integrations can evolve independently behind adapters;
- connection state is auditable without storing raw credentials in the domain table;
- future normalized health measurements can reference clear connection provenance;
- multiple paths from the same provider can coexist when required for deduplication.

Costs:

- secret management becomes a separate infrastructure concern;
- adapters must translate provider-specific permissions into normalized application keys;
- later health-measurement ingestion must preserve enough provenance to identify duplicate events arriving through different connections.
