# ADR-062 — Automatic restrictions and visible base recipe alternatives

Date: 2026-10-18
Status: implemented locally, pending integration

## Context

The Family explicitly requested automatic preselection from active diets/conditions and
visible ingredient alternatives on familiar base recipes. The manual-only defaults in
ADR-061 no longer match that request.

## Decision

Resolve restrictions from the selected participants, dates and meal types. Use the
effective nutrition plan compiler for structured food exclusions and confirmed FODMAP
diet guidance. Map the canonical `sibo` condition to the Family-requested FODMAP planning
profile; only reported/confirmed conditions within their date interval participate.
Resolved, suspected, future or absent participants' conditions do not activate it.
Other conditions without a mapping produce a visible warning rather than guessed rules.

Show automatic selections with person, origin and applicable dates. Keep them separate
from manually saved week exclusions, so removing a participant or resolving a condition
does not leave an old automatic selection stored as a manual rule. Recompute automatic
restrictions per slot during both weekly proposal and acceptance. Existing personal
plan gates remain in place. No permanent NutritionConstraint is created from a diagnosis.

Keep base recipe names and show each affected ingredient as `original → alternative`,
with reason, other non-rejected proposals, review state and missing quantity. Link store
candidates from the same ingredient. Existing executable transformations show their
actual ingredient change directly in the weekly grid; existing unadapted recipes can
show pending changes in that grid.

## Limits

This is a configured planning profile, not a clinical SIBO prescription or a permanent
elimination phase. Educational high-FODMAP mappings are not portion-specific lab data.
Base recipe adaptation cards are proposals. Missing quantities/composition and complete
multi-operation variant validation remain unresolved: such drafts cannot be silently
materialized or used as substituted shopping quantities. The executable weekly planner
still rejects an unchanged base recipe that violates the effective restrictions.

The low-FODMAP profile needs individualized phase/tolerance controls in a future increment.
Do not generalize the SIBO mapping to arbitrary condition names or free-text plan titles.

Sources for cooking proposals:
[Monash onion/garlic alternatives](https://www.monashfodmap.com/blog/cooking-with-onion-and-garlic-myths-and/)
and [Monash recipe modification](https://monashfodmap.com/blog/modifying-recipes-high-fodmap-to-low/).

## Validation

98 web tests passed, including rendered base recipe/change/reason/missing-dose evidence;
TypeScript, production build, Ruff and diff whitespace checks passed. The full API run
passed 361 tests and identified one request-cache ordering regression. After moving
automatic evaluation after context compilation, all 23 weekly/workspace integration
tests passed, including that regression. Tests cover attendance, condition date/status,
Family scope, effective plan validity/meal scope and server preview/accept enforcement.
Local browser verification shows automatic selections for an affected participant and Mac and Cheese's
milk/pasta alternatives. No actual meal was applied during this UI verification.
