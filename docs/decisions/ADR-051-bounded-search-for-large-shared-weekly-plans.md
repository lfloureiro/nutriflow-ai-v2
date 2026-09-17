# ADR-051: Large shared weekly plans use bounded deterministic search

- Status: Accepted
- Date: 2026-09-17

## Context

PR #54 exposed a server-authoritative shared weekly proposal API over the existing shared practical recommendation and Person-specific Meal Plan-Fit evidence. The shared weekly optimizer still enumerated the complete Cartesian product of eligible candidates and refused any search space above the explicit `max_combinations` limit.

That exact-search boundary is useful for small planning problems but does not scale to an ordinary week. Fourteen slots with two eligible alternatives already produce 16,384 complete combinations, while the API limit is 10,000. Increasing the hard limit only postpones the problem and makes request cost unpredictable.

Nutrition safety must not be weakened to make search cheaper. Mandatory weekly maxima, same-day nutrient upper bounds, unknown-evidence fail-closed behaviour and Person-specific portions remain authoritative.

## Decision

Add a search-strategy layer above the existing shared weekly optimizer.

When the complete eligible search space fits inside the supplied budget, the established exact optimizer remains unchanged and is used directly.

When the complete search space exceeds the budget, use a bounded deterministic search that expands the week slot by slot. Every retained partial state is evaluated through the existing shared combination evaluator, which in turn projects the choices through every Person's existing weekly optimizer. No nutrition, classification, frequency or daily-limit rule is reimplemented in the search layer.

Partial states that already fail a mandatory weekly maximum, mandatory same-day daily limit or other Person-specific hard gate are discarded immediately. Such upper-bound failures cannot become safe by adding later meals.

The bounded path ranks feasible partial states with the same shared weekly ranking already used for complete plans, plus deterministic candidate/order tie-breaks. Because the search is bounded, it can discard a partial state that would have led to a globally better final plan. Therefore bounded results are explicitly marked as truncated and must not be represented as exact optima.

The proposal API exposes:

- `search_strategy`: `exact` or `bounded`;
- `search_space_size`: size of the full eligible Cartesian product;
- `search_truncated`: whether the bounded strategy pruned the search space.

The existing `max_combinations` request field acts as the deterministic search-evaluation budget for the bounded path while preserving its previous exact-search meaning for small spaces.

## Consequences

- Ordinary multi-slot weeks no longer fail solely because their Cartesian product exceeds 10,000 combinations.
- Hard nutrition gates remain server-authoritative and Person-specific.
- Small search spaces preserve exact behaviour and existing ranking semantics.
- Large-search results are deterministic but approximate; the API makes that explicit.
- Proposal generation remains non-persistent and does not create MealEvents.
- No database migration is required; Alembic head remains `d2e6f1a9c4b7`.
- A later optimization slice may replace the bounded strategy with a more sophisticated solver without changing the nutrition-evidence boundary.
