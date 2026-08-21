# ADR-004 — Health providers are abstracted behind a common model

## Status
Accepted

## Decision

NutriFlow AI v2 will not expose provider-specific health payloads directly to planning logic.

Each provider integration maps into a normalised health model with provenance and deduplication support.

## Initial providers

The architecture must support at least:

- Apple Health / HealthKit;
- Android Health Connect;
- Garmin;
- Withings;
- Oura;
- Fitbit;
- future providers.

Not all providers need to be implemented in the first release.

## Core rules

- health connections belong to Person;
- authorisation is explicit and granular;
- imported records retain provider/source provenance;
- duplicate paths between providers must be detectable;
- raw measurements are separated from derived DailyHealthState;
- planning consumes normalised/derived state, not provider SDK objects.

## Rationale

People may use different ecosystems, and the same measurement can travel through more than one provider. Without a provider abstraction NutriFlow would accumulate provider-specific branches throughout nutrition logic and could double-count data.

## Consequences

Provider adapters can evolve independently. Replacing or adding an integration should not require rewriting the planner.
