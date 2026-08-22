# ADR-031: Web planning bootstrap discovers persisted state and composition evidence

## Status

Accepted

## Context

The first NutriFlow web recommendation vertical slice intentionally proved the real Person -> recommendation -> decision flow before broadening the API. Because the backend recommendation contract requires explicit persisted `DailyNutritionState` and Food/Recipe composition snapshot IDs, the initial UI exposed those UUIDs as development inputs.

That is not an acceptable long-term user interaction. The web client needs a way to discover the current persisted planning evidence without weakening the existing trust boundary by letting the browser author nutrition totals, select another Family's catalogue data, or silently use future composition evidence.

A general catalogue/search platform and automatic DailyNutritionState refresh are larger concerns. The immediate need is a focused read boundary that removes technical IDs from the normal web workflow while preserving the current deterministic recommendation contracts.

## Decision

Add a read-only person-scoped planning bootstrap endpoint:

```text
GET /api/persons/{person_id}/planning-bootstrap?scheduled_at=<timezone-aware instant>
```

The endpoint:

- requires a timezone-aware planning instant;
- derives the planning date in the persisted Person timezone;
- returns the latest persisted DailyNutritionState for that local date, or `null` when none exists;
- returns active global or same-Family FoodItem/Recipe candidates only;
- returns one latest composition snapshot per catalogue object that is valid as of the planning instant;
- exposes persisted composition IDs plus display/reference metadata needed by the web UI;
- never accepts client-authored nutrition values as evidence.

Food compositions are eligible only when `effective_at <= scheduled_at`. Recipe compositions are eligible only when `computed_at <= scheduled_at`.

The endpoint does not run recommendation safety/ranking and cannot make an ineligible candidate eligible. Existing practical recommendation and decision services remain authoritative.

## Why not create state automatically here

DailyNutritionState is derived state with explicit recalculation and target semantics. Bootstrap reads existing persisted evidence only. Automatically recalculating or inventing a target inside a read endpoint would couple discovery to write/derivation policy that is not yet fully decided.

A missing state is therefore returned explicitly as `null` and will be handled by a later focused refresh/target-selection increment.

## Why not build full catalogue search now

The immediate web need is to stop pasting UUIDs. A full search service introduces pagination, text search, semantic meal categories, provider data, potentially localization and ranking. Those capabilities are useful but not required to preserve the current vertical slice.

The bootstrap endpoint deliberately returns a minimal deterministic catalogue view first. Search/pagination can later replace or sit behind the same UI without changing recommendation safety semantics.

## Consequences

Benefits:

- the web UI can hide technical DailyNutritionState and composition IDs;
- the browser continues to reference persisted server evidence rather than author nutrition totals;
- Family isolation is enforced server-side;
- planning date follows the Person timezone;
- future composition snapshots are not accidentally used for past/current planning;
- the existing recommendation API contract remains unchanged.

Costs and limitations:

- catalogue discovery is not yet paginated or searchable;
- missing DailyNutritionState remains a visible state rather than being recalculated automatically;
- the endpoint does not yet distinguish finished meal candidates from ingredients/supplements semantically;
- authentication/current-family discovery remains outside this increment.

## Follow-up

The next web increment should consume this endpoint to replace manual DailyNutritionState/composition UUID inputs with normal state/candidate selection. Later increments may add catalogue search, automatic daily-state refresh/target selection and authenticated user/family context.
