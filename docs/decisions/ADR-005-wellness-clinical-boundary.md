# ADR-005 — Wellness first; clinical constraints are externally defined

## Status
Accepted

## Decision

NutriFlow AI v2 initially operates as a wellness and nutrition-planning product, not as autonomous diagnostic or treatment software.

Medical or dietetic constraints may be stored and enforced when provided by the user, doctor or nutritionist, but NutriFlow should not independently diagnose a condition and prescribe clinical treatment as though it were a clinician.

## Requirements

- every important restriction can store provenance;
- clinician/nutritionist rules can be marked mandatory;
- mandatory rules are evaluated before recommendations and ML ranking;
- the system can surface unusual trends and recommend review without claiming a diagnosis;
- any future feature that moves toward diagnosis/treatment requires a regulatory and safety review.

## Rationale

NutriFlow can provide sophisticated adaptive nutrition while maintaining a clear product boundary. This reduces safety risk and prevents recommendation algorithms from silently overriding professional guidance.

## Consequences

The architecture keeps professional supervision and clinical provenance first-class, while the recommendation engine remains constrained by explicit rules.
