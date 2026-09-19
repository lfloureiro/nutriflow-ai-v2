# ADR-050: Weekly planning API is server-authoritative

## Status

Accepted.

## Context

Phase 8c now has deterministic one-Person and shared-Family multi-slot optimizers. Those optimizers deliberately consume already evaluated recommendation and Meal Plan-Fit evidence rather than loading plans, classifying foods or recalculating nutrition themselves.

A browser-facing weekly planning endpoint therefore needs an orchestration boundary. Asking the client to submit `CandidateEvaluation`, `MealPlanFitRead` or weekly progress evidence would make safety-relevant planning state client-authoritative and would allow stale or mismatched evidence to enter the optimizer.

The existing shared practical recommendation pipeline already owns the server-side work needed for each slot: planning bootstrap, catalogue loading, Person-specific portions, Meal Plan-Fit, practical availability, weekly frequency support, diversity and feedback.

## Decision

The weekly planning proposal API accepts only ordinary planning inputs:

- Family path identity;
- selected Person IDs;
- future planning slots;
- candidate composition identities and quantities;
- practical context such as kitchen, time, location and allowed source kinds;
- an explicit deterministic combination limit.

For every slot the server runs the existing shared practical recommendation pipeline. The exact Person-specific `MealPlanFitRead` used for that candidate is carried transiently with each shared participant evaluation. Diversity and feedback adjustments preserve that transient evidence.

The weekly orchestration layer then converts those server-generated slot evaluations into `SharedWeeklyPlanningSlot` inputs and calls the existing shared-Family optimizer. It does not:

- compile or reinterpret NutritionPlan rules;
- accept Plan-Fit evidence from the client;
- calculate weekly frequency progress independently;
- classify food from names or descriptions;
- duplicate weekly maximum or same-day daily nutrient coupling logic.

The proposal response exposes the selected weekly combination, Person-specific portions/scores/explanations, optimization counters and per-slot recommendation engine versions. If a requested slot has no server-authoritative eligible candidate after practical availability and Plan-Fit evaluation, that slot is returned explicitly as skipped/pending and is not allowed to collapse the search space for otherwise feasible slots. Internal Plan-Fit objects remain server-side.

## Persistence boundary

Generating a weekly proposal does not create `MealEvent`, `MealParticipant` or `Serving` rows. The endpoint may prepare the same derived `DailyNutritionState` required by existing recommendation flows, but the proposed meals themselves remain uncommitted.

Acceptance/materialization of a weekly proposal is a separate capability. That future boundary must revalidate authoritative evidence and define transaction/conflict semantics for creating several MealEvents together rather than treating proposal generation as implicit acceptance.

No schema migration is required for this decision.

## Consequences

- The browser cannot forge or reuse stale safety evidence.
- Weekly optimization consumes the exact Person-specific evidence produced by the recommendation path for each slot.
- Operationally impossible slots remain explicit pending gaps; they are not silently filled, and they do not invalidate otherwise feasible weekly choices.
- Existing single-slot recommendation behavior remains compatible because the new Plan-Fit field is transient and optional outside Plan-Fit paths.
- Shared weekly planning remains a composition layer over established evaluators instead of becoming another nutrition engine.
- Proposal generation and proposal acceptance can evolve independently.

## Follow-up

The next focused increment should add explicit weekly proposal acceptance/materialization with revalidation and transactional conflict handling. UI work under `Refeições -> Semana` can then consume proposal and acceptance APIs without owning nutrition logic.
