# ADR-047 — Full-week planning consumes Meal Plan-Fit evidence

## Status

Accepted.

## Context

Phase 8a established Person-specific weekly frequency progress. Phase 8b extended Meal Plan-Fit so one candidate can be evaluated against that progress and recommendation ranking can prefer candidates that support a confirmed weekly minimum. The shared-Family extension kept the same evidence Person-specific while preserving hard-gate precedence.

Those slices intentionally evaluate one meal candidate at a time. A full-week planner has an additional responsibility: several individually safe choices can become unsafe or suboptimal when selected together. For example, two candidates may each fit below a weekly maximum when evaluated independently, while selecting both would exceed that maximum. Likewise, repeatedly rewarding the same minimum-support statement can over-count a deficit that only needs one more occurrence.

The week-level planner must solve these composition effects without becoming a second nutrition or food-classification engine.

## Decision

The Phase 8c planner is a deterministic composition layer over existing recommendation and Meal Plan-Fit evidence.

For each Person and future meal slot, its inputs are already evaluated candidate pairs:

```text
CandidateEvaluation + MealPlanFitRead
```

The planner does not:

- compile NutritionPlans independently;
- recalculate weekly progress from MealEvents;
- infer food categories from names or descriptions;
- reinterpret nutrition constraints;
- turn weekly minimums into per-slot hard requirements.

Meal Plan-Fit remains authoritative for candidate-level safety, numeric rules and weekly-frequency classification. Phase 8c only composes that structured evidence across several slots.

### Structured weekly match evidence

Meal Plan-Fit weekly guideline output now preserves two additional facts from its existing frequency evaluation:

```text
candidate_matches: true | false | null
unclassified_meal_count: integer | null
```

`candidate_matches` is produced by the existing structured candidate classifier. `null` means unknown; it is never treated as false.

`unclassified_meal_count` preserves the uncertainty already present in weekly progress when counts are lower bounds. These fields let the planner compose several choices without parsing explanation text or creating a second classifier.

### Hard-gate composition

Only candidates that are already eligible in both recommendation and Meal Plan-Fit may enter a feasible combination.

Mandatory weekly maxima are then rechecked for the selected combination because individually eligible candidates can jointly exceed the cap.

For a mandatory maximum, safe capacity must be provable from structured evidence. The planner uses the conservative possible count:

```text
current confirmed occurrences
+ existing unclassified meals when counts are lower bounds
+ selected known matches
+ selected unknown candidate matches
```

If that possible count exceeds the mandatory maximum, the entire combination is infeasible. Unknown evidence therefore fails closed where the combined plan cannot prove safety.

### Weekly minimum objective

A confirmed weekly minimum remains an ordering objective, not a hard obligation for every slot.

For each guideline, the planner calculates only the confirmed remaining deficit. When current counts are lower bounds, existing unclassified meals are included in the possible existing count before calculating that confirmed deficit.

Selected `support` results can satisfy the objective only up to that remaining deficit. Therefore a target that needs one more occurrence can contribute at most one unit of week-level support even if several selected meals match it.

Ordering among feasible combinations is deterministic:

1. more supported occurrences toward mandatory confirmed weekly minimum deficits;
2. more supported occurrences toward advisory confirmed weekly minimum deficits;
3. higher minimum candidate score across the week;
4. higher average candidate score;
5. fewer exact candidate repeats when all prior criteria tie;
6. stable candidate-key tuple.

Weekly support remains separate from numeric `fit_score`.

### Search boundary

The first Phase 8c slice uses explicit deterministic enumeration with a hard combination limit. It refuses a search space above the configured limit instead of silently truncating candidates or returning an approximate result as if it were globally optimal.

This is a foundation for later bounded/advanced optimization, not a claim that exhaustive enumeration is the final production strategy.

### Scope of this slice

The v1 foundation optimizes one Person over several slots in one Monday-Sunday week. It establishes the evidence contract, hard maximum composition and minimum-deficit objective.

Deferred increments include:

- joint projected daily nutrient state across several slots on the same day;
- simultaneous shared-Family slot choices with Person-specific portions and fairness;
- category/protein diversity across the proposed week beyond exact-candidate tie breaking;
- pantry depletion and shopping-list coupling;
- schedule/preparation capacity coupling;
- commercial availability windows and restaurant/delivery allocation;
- scalable search/optimization beyond the explicit enumeration limit;
- persistence/API workflow for accepting a generated weekly proposal.

## Consequences

- Phase 8c reuses Meal Plan-Fit instead of creating competing rule semantics.
- Missing classification remains unknown rather than becoming zero or a non-match.
- Mandatory weekly maxima remain safe when several individually eligible choices are combined.
- Weekly minimum support cannot be over-counted past the confirmed remaining deficit.
- The optimization result is reproducible for identical ordered evidence.
- No database migration is required for this foundation slice.
