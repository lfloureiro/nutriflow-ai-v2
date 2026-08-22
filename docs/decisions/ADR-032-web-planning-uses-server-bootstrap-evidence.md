# ADR-032: Web planning uses server bootstrap evidence

## Status

Accepted

## Context

The first web recommendation vertical slice deliberately exposed `DailyNutritionState` and composition snapshot UUIDs because the recommendation API requires explicit persisted evidence. PR #26 added a read-only planning bootstrap API that resolves the current local-day state and the current valid Food/Recipe composition snapshots for a Person and scheduled instant.

The web UI now needs to remove technical UUID entry without weakening the persisted-evidence boundary or moving version-selection logic into presentation code.

## Decision

The web meal-planning flow will obtain state and candidate evidence only through:

```text
GET /api/persons/{person_id}/planning-bootstrap?scheduled_at=...
```

The browser displays names, brands, reference servings and energy metadata, while retaining the returned composition IDs internally for the subsequent practical recommendation request.

Rules:

- the browser does not derive a DailyNutritionState ID from timestamps;
- the browser does not choose a composition version from catalogue history;
- changing Person or scheduled instant reloads bootstrap evidence;
- a missing DailyNutritionState is shown explicitly and disables recommendation submission;
- an empty bootstrap catalogue is shown explicitly;
- selecting a Food/Recipe candidate initializes quantity/unit from the server-provided reference serving;
- users may adjust requested quantity/unit, but the candidate identity remains the server-selected persisted composition;
- duplicate selected composition IDs are prevented in the current form;
- recommendation eligibility, exclusion and ranking remain entirely server-authoritative.

## Consequences

The normal web flow no longer requires users to paste `DailyNutritionState` or composition UUIDs. Technical IDs remain part of the API contract and audit trail but are not user-facing planning inputs.

The Family UUID remains a temporary development entrypoint until authentication and explicit household authorization context are implemented.

Missing daily state is not auto-created in this increment. Background/event-driven state refresh and target-selection policy remain separate backend work.
