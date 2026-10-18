# ADR-060: Resolve participants before recipe variants and source discovery

## Status

Accepted product direction requested on 2026-10-18. Implementation pending; ADR-059 is the implemented review baseline.

## Decision

Meal context is date/time + participating group + location/source intent. Weekly attendance patterns and date exceptions resolve explicit participants per meal before candidate evaluation. One Family-wide participant list must not substitute for a heterogeneous week's individual/shared groups.

Reuse Person, Family, ScheduleEntry, MealEvent/MealParticipant/Serving and existing individual/shared nutrition evaluators. Introduce attendance/per-slot orchestration without a second nutrition engine.

When an explicit applicable participant restriction requires adaptation, present a reviewed active Family recipe variant eligible for all participants in place of an incompatible original. Do not infer a diet from a disease, impose an absent person's rules, or fall back to an incompatible recipe when evidence is missing. Revalidate on presence/context/rule/composition changes and before applying.

Expose recipes, delivery dishes and restaurant/menu discovery in one meal-planning flow; keep provider configuration secondary. A venue and a dish with assessed nutrition/restrictions remain distinct evidence states.

Marketplace connectors need authorized executable integrations and observed responses. Flags, merchant/POS credentials and synthetic fixtures do not prove consumer discovery availability. Unknown required food evidence cannot be rescued by price, stars or proximity.

## Consequences

- Patterns/exceptions reduce repeated attendance entry while retaining uncertainty.
- Individual/shared meals coexist and project nutrition per Person.
- Family variants preserve original recipes and support complete operation sets.
- Independent source failures preserve useful results and honest capability states.
- Diagnoses/history stay local; external services receive only necessary authorized context.
- Normal users decide from the meal; source screens become secondary tools.

Detailed implementation sequence: `docs/vision/integrated-family-meal-planning-roadmap.md`.
