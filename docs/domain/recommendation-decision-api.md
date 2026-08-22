# Recommendation decision API

## Purpose

This increment exposes the next write boundary after a persisted meal recommendation run.

A client can make one explicit decision about a persisted `MealRecommendationOption` through:

```text
POST /api/recommendation-options/{option_id}/decision
```

The endpoint supports the existing domain actions:

- `accepted`;
- `rejected`;
- `modified`.

It does not recompute recommendation ranking. The option is already persisted evidence from the recommendation engine.

## Accepted decisions

An accepted decision requires:

- a persisted eligible `MealRecommendationOption`;
- timezone-aware `scheduled_at`;
- explicit timezone.

The API delegates to the existing recommendation-planning service. The resulting plan uses the option's exact recommended quantity and unit.

The operation creates:

```text
MealRecommendationFeedback(action=accepted)
-> MealEvent(status=planned)
-> MealParticipant(status=planned)
-> Serving(status=planned)
```

The Serving keeps the recommendation option's catalogue/composition provenance and recalculates planned nutrition through the established Serving nutrition service.

Supplying a different quantity or unit while claiming `accepted` remains invalid. Quantity changes require `modified`.

## Modified decisions

A modified decision has the same scheduling requirements as an accepted decision but may override the recommended quantity/unit and normal plan presentation fields.

The existing domain service remains authoritative for:

- positive quantity;
- accepted-versus-modified semantics;
- meal type resolution;
- exact composition requirement;
- Serving nutrition recalculation;
- Person and recommendation provenance.

Unsafe quantity conversions are returned as semantic API validation failures rather than server errors.

## Rejected decisions

A rejected decision records append-only recommendation feedback and creates no MealEvent, MealParticipant or Serving.

Meal-planning fields are rejected for `action = rejected` so a request cannot ambiguously combine refusal with plan creation.

Optional `feedback_metadata` may record client/user context such as a rejection reason. It remains feedback evidence rather than authoritative meal state.

## Persistence and response

The endpoint returns persisted identifiers for the created feedback event and, when materialized, the resulting MealEvent and Serving.

For accepted/modified decisions the response includes:

- feedback ID;
- recommendation option ID;
- action;
- resulting Serving ID;
- MealEvent ID/status/scheduled time;
- planned quantity/unit;
- planned energy.

For rejected decisions all meal/Serving fields are null.

## Error semantics

The API uses:

- `404` when the recommendation option does not exist;
- `422` when the requested decision violates domain or input semantics.

Examples of `422` include:

- materializing an ineligible option;
- accepted/modified without schedule information;
- rejected with meal-planning fields;
- accepted with a changed recommended quantity/unit;
- unsupported/unsafe Serving quantity conversion;
- invalid feedback-domain semantics.

## Safety boundary

The endpoint never changes recommendation eligibility.

An excluded option cannot become a planned meal through this API. The existing hard-rule-first recommendation result is persisted before this decision boundary, and `materialize_recommendation_option()` independently refuses ineligible options.

The endpoint also never accepts client-authored nutrition totals. Planned Serving nutrition is recomputed from the exact persisted composition snapshot linked to the recommendation option.

## Current idempotency limitation

Recommendation feedback is append-only and this endpoint currently represents a single explicit decision command. It does not yet provide a request idempotency key for retries or transaction-level duplicate suppression.

MealEvent already has Family-scoped idempotency infrastructure elsewhere in the domain, but this decision endpoint does not yet bind the recommendation decision to that mechanism.

Do not assume retry safety for duplicate/concurrent submissions. Transaction-level API idempotency remains a focused future increment and must not be approximated by silently deduplicating feedback metadata.

## Non-goals

This increment does not:

- expose shared-family recommendation acceptance;
- orchestrate practical pantry/commercial recommendation context;
- add shopping-list persistence;
- add authorization/authentication policy;
- add request-level idempotency or concurrent duplicate suppression;
- replace MealEvent/Serving with recommendation-specific plan tables.
