# Health measurement model

## Purpose

`HealthMeasurement` is the normalized quantitative health-observation layer used by NutriFlow AI v2.

Provider-specific payloads must be translated into this model before nutrition logic consumes them. The model therefore separates provider integration concerns from normalized health semantics.

The goals are to:

- retain the Person that owns the observation;
- preserve enough provenance to explain where the data came from;
- support both point-in-time and interval measurements;
- retain the ingestion path and the underlying origin when known;
- prevent the same underlying event from being counted twice when it arrives through multiple provider paths;
- allow normalization rules to evolve without making historical records uninterpretable.

## Ownership

Every HealthMeasurement belongs to exactly one `Person`.

A measurement may reference the `HealthConnection` through which it was imported. The connection reference is optional because historical measurements should remain valid if a connection is later removed.

Deleting a Person removes their measurements. Deleting a HealthConnection does not delete historical measurements; the connection foreign key is cleared instead.

## Normalized measurement identity

Each record contains:

- `metric`: stable NutriFlow metric key such as `resting_heart_rate`, `active_energy`, `steps` or `weight`;
- `value`: normalized numeric value;
- `unit`: normalized unit understood by NutriFlow;
- `normalization_version`: version of the mapping/normalization rules used to produce the record.

Provider-specific field names must not leak into the metric key.

## Temporal shapes

HealthMeasurement supports two mutually exclusive temporal shapes.

### Point observation

A point observation has:

- `observed_at`;
- no `period_start_at`;
- no `period_end_at`.

Examples:

- resting heart rate;
- body weight;
- instantaneous heart-rate sample.

### Interval observation

An interval observation has:

- `period_start_at`;
- `period_end_at`;
- no `observed_at`.

Examples:

- active energy over a workout or time window;
- steps over an aggregation period;
- sleep duration over a sleep interval.

The database validates that a record uses exactly one valid temporal shape and that interval end is not earlier than interval start.

## Provenance

Provider is the route through which NutriFlow received the normalized record.

`origin_provider` identifies the underlying origin when that can be determined.

This distinction is important for data that travels through bridges such as:

Garmin Watch
-> Garmin Connect
-> Apple Health
-> NutriFlow

A record received from Apple Health can therefore have:

- provider: `apple_health`;
- origin_provider: `garmin`;
- source_device: `Garmin Watch`;
- source_app: `Garmin Connect`;
- source_chain: `["garmin_watch", "garmin_connect", "apple_health"]`.

Additional provenance fields include:

- `health_connection_id`;
- `source_kind`;
- `source_device`;
- `source_app`;
- `external_id` for the record in the ingestion provider;
- `origin_external_id` for the underlying source record when known;
- `source_chain`;
- optional non-secret `provenance_metadata`.

Raw credentials must never be stored in HealthMeasurement.

## Deduplication

The same physical event can reach NutriFlow more than once.

Example:

Garmin API
-> NutriFlow

and:

Garmin Watch
-> Garmin Connect
-> Apple Health
-> NutriFlow

Both paths may describe one underlying activity.

Every normalized HealthMeasurement therefore requires a `deduplication_key`.

The ingestion/normalization layer is responsible for producing this key. Preferred inputs are, in order:

1. a stable underlying provider record identifier;
2. origin provider plus origin external identifier;
3. when no reliable origin identifier exists, a deterministic fingerprint built from canonical metric, temporal boundaries, normalized value/unit and stable provenance signals.

The database enforces uniqueness of `(person_id, deduplication_key)`.

This means two different Persons can legitimately have the same provider identifier, but one Person cannot persist the same canonical health event twice.

A provider's local `external_id` alone is not sufficient for cross-path deduplication because the same underlying event can receive different identifiers when bridged through another platform.

## Normalization versions

Normalization behavior can evolve as provider APIs and NutriFlow mappings improve.

`normalization_version` records the mapping version that produced a measurement. Historical data is therefore explainable even after a later normalization version is introduced.

Reprocessing imported data must not silently mutate provenance. If records are replaced or recalculated in future workflows, the process must preserve traceability between old and new normalized interpretations.

## Relationship with anthropometric history

`AnthropometricMeasurement` currently stores the core historical body-measurement domain used by person/nutrition calculations.

HealthMeasurement is the normalized health-integration layer.

A future ingestion service may project selected normalized health metrics, such as weight, into the anthropometric history according to explicit reconciliation rules. The two tables must not be implicitly double-counted.

## Relationship with derived daily state

HealthMeasurement is source data, not a daily summary.

Future `DailyHealthState` logic will derive compact daily context from normalized measurements such as:

- steps;
- active/resting energy;
- workouts;
- sleep;
- resting heart rate;
- HRV;
- body measurements.

Derived state must remain recalculable from normalized source records.
