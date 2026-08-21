# Health connection model

## Purpose

`HealthConnection` represents one configured health-data integration for one Person.

Connections are person-scoped because health permissions, provider accounts and imported measurements belong to an individual rather than to a Family as a whole.

The model supports both device-mediated health platforms and cloud-provider APIs without coupling the domain to one vendor.

## Provider abstraction

`provider` is an extensible application-level key.

Initial provider keys are expected to include:

- `apple_healthkit`;
- `android_health_connect`;
- `garmin`;
- `oura`;
- `withings`;
- `fitbit`.

Provider-specific SDK or API behaviour belongs behind adapters. The domain record stores connection state and provenance, not provider-specific business logic.

## Connection identity

A Person may have multiple health connections.

Each connection is identified by the combination of:

- `person_id`;
- `provider`;
- `connection_key`.

`connection_key` is a stable NutriFlow-level identifier for that connection. It allows more than one account or connection path for the same provider when required.

`connection_kind` describes the integration path, for example:

- `device_bridge` for local/platform-mediated sources such as HealthKit or Health Connect;
- `cloud_api` for direct provider APIs such as Garmin, Oura or Withings.

The values remain extensible rather than being fixed to a database enum.

## Lifecycle

Supported connection states are:

- `pending`;
- `active`;
- `paused`;
- `error`;
- `revoked`.

New records default to `pending`.

`revoked_at` records explicit revocation time. When it is populated, the connection status must be `revoked`.

A revoked row should normally be retained for audit/provenance. Reconnecting should create or deliberately reactivate an appropriate connection according to provider behaviour rather than deleting history silently.

## Permissions

`permissions` stores the scopes or health-data categories granted to NutriFlow for this connection.

Examples include:

- steps;
- workouts;
- active energy;
- resting energy;
- body measurements;
- sleep;
- heart rate;
- HRV.

Permissions are provider-normalized application keys. Provider-specific scope strings may be retained inside provider metadata when necessary, but nutrition logic should consume normalized capabilities.

## Sync state

A connection may store:

- opaque `sync_cursor` state;
- `last_sync_attempt_at`;
- `last_successful_sync_at`.

These fields support incremental import and operational visibility without making HealthConnection itself a store for normalized measurements.

Imported measurements will be modeled separately and reference sufficient provenance for deduplication.

## Provider account metadata

`provider_account_id` may store the external account identifier when the integration exposes one.

`provider_metadata` can retain non-secret provider-specific connection metadata needed by an adapter.

It must not become an unrestricted dump of raw health measurements.

## Credential handling

Raw access tokens, refresh tokens, API secrets and similar credentials must not be stored directly in `health_connections`.

`credential_reference` is an optional opaque pointer to an external secret-management mechanism.

For integrations that do not use server-held credentials, such as some device-bridge flows, it may remain null.

This separation prevents the domain table from becoming a credential store and allows credentials to be rotated independently from the connection record.

## Relationship to normalized health data

HealthConnection describes how data enters NutriFlow.

The next domain layer will describe the normalized measurements themselves.

A normalized health measurement will need provenance sufficient to distinguish paths such as:

Garmin device -> Garmin Connect -> Apple Health -> NutriFlow

from:

Garmin device -> Garmin API -> NutriFlow

The same underlying event may appear through both paths. Connection provenance, provider identifiers, external event identifiers, device information and event timing will contribute to later deduplication logic.

## Security and access boundary

Family membership does not grant implicit access to another Person's connected health data.

Authorization must remain person-scoped even when household meal planning is shared.

HealthConnection stores connection metadata only. It does not alter the wellness boundary: NutriFlow may use health and professional constraint data to support nutrition planning, but it must not autonomously diagnose disease or prescribe medical treatment.
