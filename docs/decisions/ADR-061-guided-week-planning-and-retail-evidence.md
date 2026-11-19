# ADR-061 — Guided week planning and retail evidence

Date: 2026-10-18
Status: implemented locally, pending integration

## Context

Users could not identify where to start next week's meals, select restrictions or reach
the resulting shopping list. Ingredient review also lacked concrete supermarket options.

## Decision

Expose one guided path from Home and Plan: choose week and common participants, review
explicit ingredient exclusions, generate/review/apply, then shopping. Persist versioned
Family week choices. Reuse existing personal plan checks and enforce additional exclusions
in both proposal and materialization. A diagnosis does not activate a diet.

Keep retail observations separate from food composition and FODMAP evidence. Offer them
beside relevant review/shopping ingredients with source, pack, date and evidence tier.
No silent recipe replacement, cart operation or inferred FODMAP certification.

Use a frozen composition's batch basis for legacy shopping only if it matches the current
recipe exactly; expose inferred serving counts as approximate quantities.

## Consequences

The weekly workflow is discoverable and connected. The current generator still uses
one shared group of at least two people. ADR-060 remains the target for per-slot attendance,
complete variants and unified delivery/restaurant discovery. Retail coverage starts with
four reviewed observations, not a complete or live supermarket catalogue.

Implementation and validation: `../domain/guided-week-planning-and-retail-alternatives.md`.
