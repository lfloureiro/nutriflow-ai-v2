# ADR-029: Practical recommendation orchestration uses any-source evidence

- Status: Accepted
- Date: 2026-08-22

## Context

NutriFlow already has deterministic nutrition/safety recommendation logic plus separate operational models for schedule context, persisted meal-source availability, pantry stock and commercial opening/offer data.

The first recommendation API exposed in ADR-027 intentionally accepts explicit persisted DailyNutritionState and composition snapshots, but it does not combine those practical inputs. A web client should not need to reproduce source-merging rules or decide how unknown operational evidence affects eligibility.

Practical sources are alternatives. A meal can be usable because it is available at home, can be prepared from pantry stock, or can be obtained from a restaurant/delivery/store. Treating every source as a required condition would incorrectly exclude candidates.

## Decision

Add a focused practical recommendation orchestration API that:

- keeps the existing deterministic nutrition/safety engine authoritative;
- loads Person schedule entries from persistence;
- evaluates requested practical source kinds independently;
- combines each candidate's practical source evidence using any-source semantics;
- passes one merged CandidatePracticalProfile per candidate to the existing practical recommendation engine;
- returns active commercial offers separately from nutrition/ranking output;
- persists the recommendation through the same MealRecommendationRun/MealRecommendationOption evidence model used by the base API.

### Any-source semantics

For each requested practical source channel:

- explicit available evidence is `true`;
- explicit unavailable evidence is `false`;
- missing source evidence is `unknown`.

The merged candidate availability is:

- `true` when at least one requested channel is explicitly available;
- `false` only when every requested channel has explicit unavailable evidence;
- `unknown` otherwise.

Unknown practical evidence therefore does not silently become an exclusion.

### Pantry semantics

The pantry channel combines two different responsibilities:

- quantity-aware pantry stock proves ingredient/food sufficiency;
- optional persisted `pantry` MealCandidateAvailability supplies source metadata such as location, preparation time and kitchen requirement.

When persisted pantry-source metadata exists, pantry stock sufficiency and explicit source availability are both required. Stock insufficiency is explicit pantry unavailability.

Unsafe pantry quantity conversion and unsupported recipe-yield scaling remain explicit errors rather than optimistic availability.

### Commercial semantics

`restaurant`, `delivery` and `store` are evaluated as separate channels so an explicitly closed source kind does not erase unknown evidence for another requested source kind.

Opening windows determine source usability at the requested scheduled instant. Active provider offers are returned as response metadata. Price does not change nutrition/safety eligibility or deterministic ranking in this increment.

### Request evidence

ADR-027 remains in force. The orchestration request still references:

- one persisted DailyNutritionState;
- explicit FoodCompositionSnapshot/RecipeCompositionSnapshot IDs;
- explicit candidate quantities/units.

This increment does not introduce client-authored nutrition totals or automatic catalogue-wide candidate discovery.

## Consequences

### Positive

- UI clients get one coherent practical recommendation boundary.
- Schedule, source, pantry and commercial rules stay server-side and deterministic.
- Alternative practical sources are modeled correctly rather than as an accidental AND condition.
- Missing operational metadata remains distinguishable from explicit unavailability.
- Commercial offers can be displayed without allowing price/provider data to bypass hard nutrition rules.
- Existing recommendation persistence and decision APIs remain reusable.

### Trade-offs

- The request still supplies candidate composition snapshots; catalogue discovery is a separate API concern.
- Pantry evaluation can fail explicitly for candidates whose required quantities cannot be safely evaluated.
- Source freshness policy is still provider/domain metadata rather than a global rejection threshold.
- Practical source choice is not yet persisted as the selected fulfilment path when a recommendation is accepted.

## Rejected alternatives

### Require every requested source to be available

Rejected because home, pantry and commercial sources are alternatives, not simultaneous requirements.

### Treat missing source evidence as unavailable

Rejected because existing practical-domain semantics distinguish unknown operational state from explicit unavailability.

### Let the web client merge practical source data

Rejected because it would duplicate safety-relevant deterministic semantics across clients and make audit behaviour inconsistent.

### Rank directly by commercial price

Rejected for this increment. Commercial data remains advisory/contextual until an explicit optimization policy is defined.
