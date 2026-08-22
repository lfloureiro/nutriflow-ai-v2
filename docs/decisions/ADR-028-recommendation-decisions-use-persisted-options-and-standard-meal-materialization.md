# ADR-028: Recommendation decisions use persisted options and standard meal materialization

- Status: Accepted
- Date: 2026-08-22

## Context

NutriFlow already persists recommendation runs/options and already has domain services for accepted/modified recommendation materialization plus append-only feedback.

After exposing recommendation generation through the API, the next boundary is accepting, rejecting or modifying one persisted recommendation option without duplicating recommendation or meal-domain rules in the route layer.

The API must preserve hard-rule eligibility, exact composition provenance and the normal MealEvent/MealParticipant/Serving model.

## Decision

Expose:

```text
POST /api/recommendation-options/{option_id}/decision
```

The endpoint operates on an existing persisted `MealRecommendationOption`.

For `accepted` and `modified`:

- require explicit timezone-aware schedule information;
- delegate to `materialize_recommendation_option()`;
- create normal planned MealEvent/MealParticipant/Serving records;
- recalculate planned Serving nutrition from the option's exact persisted composition snapshot;
- record append-only recommendation feedback linked to the resulting Serving.

For `rejected`:

- record append-only feedback only;
- reject meal-planning fields;
- create no meal records.

An ineligible recommendation option cannot be materialized.

The API route maps not-found conditions to 404 and semantic/domain failures to 422.

## Rationale

Persisted recommendation options are the audit boundary between recommendation calculation and user decision. Recomputing or accepting client-authored nutrition at decision time would weaken reproducibility and could diverge from the safety evaluation that produced the option.

Reusing existing domain services keeps the API thin and prevents an alternate meal representation from emerging.

Separating rejected feedback from meal planning also keeps refusal evidence explicit and avoids ambiguous commands.

## Idempotency

This endpoint does not yet introduce request-level idempotency for recommendation decisions.

Feedback is intentionally append-only, while MealEvent idempotency currently lives in a separate meal-lifecycle service. Correctly composing those semantics, including concurrent retry races, requires a dedicated write-boundary design rather than ad-hoc deduplication.

Until that increment exists, clients must not assume duplicate/concurrent decision submissions are idempotent.

## Consequences

Positive:

- recommendation eligibility remains authoritative;
- exact composition provenance is retained;
- accepted/modified decisions use the standard meal model;
- rejected decisions remain pure feedback evidence;
- API behavior is deterministic and testable;
- no schema migration is required.

Trade-offs:

- the client must supply scheduling information for accepted/modified decisions;
- request-level retry idempotency remains future work;
- shared-family acceptance still needs a separate API boundary;
- authorization is outside this increment.
