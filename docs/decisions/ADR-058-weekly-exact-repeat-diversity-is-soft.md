# ADR-058: Weekly exact-repeat diversity is a soft ranking cost

## Status

Accepted.

## Context

The shared weekly planner already tracks `repeated_candidate_count`, but the count was only a late deterministic tie-break after minimum and average participant score.

That ordering is safe but produces poor weekly plans when one recipe has a small preference or diversity advantage in every independently evaluated slot. In bounded search the problem is amplified because candidate expansions can be pruned before the final repeated-candidate tie-break is able to influence the surviving beam.

The Week UI therefore can produce a technically feasible proposal that repeats the same favourite recipe across many days even though several near-equivalent eligible alternatives exist.

This problem does not require category or protein inference. Exact candidate identity is already structured evidence and can be used without inspecting names or descriptions.

## Decision

Exact candidate repetition inside one proposed shared week is a soft plan-level diversity cost.

For a feasible shared weekly plan:

- the first occurrence of a candidate has no repeat cost;
- every occurrence beyond the first increments `repeated_candidate_count`;
- each increment applies a fixed score cost of `0.2500` to both the plan-level minimum participant score and average participant score used for ranking.

The ranking remains deterministic:

```text
mandatory weekly support coverage
-> mandatory weekly support total
-> advisory weekly support coverage
-> advisory weekly support total
-> diversity-adjusted minimum participant score
-> diversity-adjusted average participant score
-> repeated candidate count
-> stable selection-key sequence
```

The repeat cost is not an eligibility rule. A repeated favourite can still win when the available alternatives are sufficiently worse.

The scalable bounded search uses the same repeat cost in its candidate expansion hint. This makes pruning aware of an immediate exact repeat instead of repeatedly preferring the same per-slot winner before the final plan ranking is evaluated.

## Safety

The repeat cost is applied only after candidates have passed recommendation eligibility and Person-specific Meal Plan-Fit.

It does not:

- relax adverse-reaction or mandatory nutrition gates;
- override mandatory weekly maxima or same-day daily limits;
- create or infer food categories from candidate names or descriptions;
- change weekly-frequency classification evidence;
- invent leftovers or treat repeated recipes as leftovers.

Mandatory and advisory weekly-plan support remains ahead of diversity in the ranking.

## Consequences

- near-equivalent eligible recipes are more likely to be distributed across the week;
- a strongly preferred recipe is still allowed to repeat;
- bounded search more closely preserves the intended weekly diversity objective;
- richer category/protein diversity remains a separate future capability and must use structured persisted metadata.

No persistence or schema migration is required.
