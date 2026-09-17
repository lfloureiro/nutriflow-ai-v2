# ADR-046 — Shared-family weekly support remains Person-specific

## Status

Accepted.

## Context

Meal Plan-Fit now evaluates weekly frequency guidance for one Person using deterministic weekly progress. Shared-family recommendations already evaluate the same candidate and a Person-specific portion independently for every participant, but the final shared ordering previously used only the minimum and average participant scores.

That meant a candidate helping one or more participants satisfy a confirmed weekly minimum could lose to another otherwise eligible candidate because the shared aggregation ignored weekly support evidence already produced by Meal Plan-Fit.

The shared layer must not create a second frequency evaluator or apply one Person's plan to another Person.

## Decision

Shared-family recommendation ordering consumes only the weekly guideline evidence already present in each participant's `MealPlanFitRead`.

For each shared candidate:

1. every participant is evaluated independently through Person-specific Meal Plan-Fit;
2. any participant-level mandatory failure, conflict, safety block or mandatory unknown continues to make the shared candidate ineligible;
3. among candidates that remain eligible for every participant, weekly `support` evidence is aggregated deterministically;
4. ordering prefers, in sequence:
   - number of participants receiving mandatory weekly-minimum support;
   - total mandatory weekly-minimum support statements;
   - number of participants receiving advisory weekly-minimum support;
   - total advisory weekly-minimum support statements;
   - existing shared minimum score;
   - existing shared average score;
   - candidate key as deterministic tie-breaker;
5. participant explanations preserve the weekly-support markers emitted by the common recommendation adapter;
6. when weekly guidance is present, the shared engine version records `shared-weekly-frequency-v1`.

Weekly support is therefore a ranking pressure only after common eligibility gates. It cannot rescue a candidate that is unsafe or incompatible with any participant's mandatory plan.

## Why participant coverage precedes raw support count

A shared meal should first prefer helping more people rather than allowing several support statements for one Person to dominate a candidate that helps multiple participants. Raw support count remains the next deterministic discriminator.

This is an aggregation policy over existing Person-specific evidence, not a new interpretation of nutrition guidance.

## Consequences

- Shared-family ranking now reflects weekly plan progress without weakening hard gates.
- One Person's weekly minimum never becomes another Person's requirement.
- The common Meal Plan-Fit service remains the only weekly-frequency evaluator.
- Existing minimum/average score fairness remains in place after weekly-support ordering.
- No persistence or migration change is required.

## Deferred

- simultaneous optimization of all meal slots across a full week;
- explicit optimization of competing participant weekly deficits across several future shared meals;
- richer reviewed food taxonomy/equivalence;
- automatic qualitative-guideline inference;
- batch optimization of candidate Plan-Fit evaluation.
