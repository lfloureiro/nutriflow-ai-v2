# ADR-059: Separate reported health conditions, educational FODMAP evidence and recipe review

## Status

Implemented on the focused health-condition/FODMAP review branch; not yet merged into main.

## Decision

Store Person health conditions with explicit status/provenance/dates and append-only revision snapshots. Require optimistic concurrency and Person/Family ownership checks. A condition does not automatically create allergies, dietary restrictions or a treatment plan.

Import only a small documented selection of public Monash educational facts. Preserve source URLs/version/date and limitations. Link food categories through explicit curated catalogue identities, never runtime guesses from names. Detailed application/calculator data and laboratory serving limits are not part of this import.

Store Family-scoped recipe substitution proposals in a separate review workspace. A proposal can have a known catalogue target or a text alternative pending composition evidence. Distinguish reference-backed public guidance from editorial ideas. Reviewed status is not safety approval or recipe application.

Existing MealPlanFit/recommendation and materialization semantics remain authoritative. Future clinical protocols and multi-operation transformations must reuse that evaluation boundary and assess the exact final portion for every participant before any suitability claim.

## Consequences

- Disease history is usable now without claiming that a diagnosis alone determines food tolerance.
- The Family can review proposed ingredient/seasoning changes without modifying global recipes or past consumption.
- Public education does not masquerade as quantitative laboratory data.
- Authenticated access and consent remain prerequisites for a production clinical record deployment; Family route scoping alone is not authorization.
- Next work is explicit protocol evidence, preparation/dose coverage and full recipe operation sets, followed by revalidation and deliberate recipe/meal application.
