# ADR-006 — Health and anthropometric data is historical

## Status

Accepted

## Decision

NutriFlow AI v2 must not store changing health or anthropometric values as current-value fields directly on `Person`.

Measurements such as weight, height, body fat, lean mass, activity, sleep and other health metrics are time-based observations and must retain their history.

`Person` represents identity and relatively stable personal attributes.

Measured values are stored as timestamped records associated with that Person.

## Rationale

Nutrition planning depends not only on a current measurement but also on its evolution.

Examples:

- weight trend over 7, 28 or 90 days;
- changes in body composition;
- activity changes;
- training frequency;
- sleep trends;
- comparison between planned nutrition and observed outcomes.

Overwriting `Person.weight` every time somebody weighs themselves would destroy the information needed to evaluate whether a nutrition strategy is working.

The same principle applies to data imported from Apple Health, Health Connect, Garmin, Withings and other providers.

## Measurement provenance

Every measurement should retain, where applicable:

- person;
- metric type;
- value;
- unit;
- measured timestamp;
- imported timestamp;
- source type;
- provider;
- source device or application;
- external identifier;
- quality or confidence metadata.

Possible sources include:

- manual entry;
- smart scale;
- Apple Health;
- Android Health Connect;
- Garmin;
- Withings;
- Oura;
- Fitbit;
- future providers.

## Derived values

Values such as:

- current weight;
- latest body-fat percentage;
- 7-day weight trend;
- 28-day activity average;
- estimated energy expenditure;

are derived state.

They may be cached for performance, but the historical measurements remain the authoritative source.

## Consequences

- `Person` does not contain a mutable `weight` field;
- historical data is never silently overwritten;
- imported health data requires provenance;
- trend calculations become possible;
- adaptive nutrition can evaluate actual outcomes over time;
- provider integrations can be added without changing the Person identity model.
