# ADR-035: Family meal planning uses explicit slots and whole-catalog recommendation

## Status

Accepted.

## Context

The first v2 recommendation screen was built as an integration slice to prove server-authoritative planning state, composition provenance, safety, ranking and recommendation decisions. It was not intended to be the final meal-planning UX.

The current visible flow exposes too much of that technical integration model: a user can manually assemble multiple candidate rows for the same Person and instant, while there is no first-class daily/weekly family planning surface. This is confusing as a product workflow and does not express the Family-first information architecture already accepted in ADR-034.

NutriFlow v1 also proved two useful product concepts that must not be lost in v2:

- a household-wide recipe catalogue with per-member 0-5 ratings and a derived family preference score;
- weekly auto-planning that previews a set of meal suggestions before applying them, while preserving already occupied slots.

v2 remains standalone: these semantics may be reimplemented and improved, but v2 must not import or depend on v1 code or schema.

## Decision

`Refeições` becomes a first-class Family planning workflow with focused secondary destinations:

```text
Refeições
├── Hoje
├── Semana
├── Pratos
└── Recomendar
```

### Hoje

`Hoje` answers: "O que está planeado para a família hoje?"

A shared meal is displayed once as one Family MealEvent, with its participants visible in summary. Person-specific exceptions or portions are drill-down details rather than duplicate top-level meal cards.

### Semana

`Semana` answers: "O que está planeado para esta semana?"

The screen supports viewing and editing a whole planning horizon. A dedicated `Planear semana` action produces a preview before anything is persisted. Existing/locked slots remain unchanged unless the user explicitly replaces them.

### Pratos

`Pratos` is the human catalogue of meals/recipes that can be considered for planning. It exposes suitability, family preference information and relevant planning metadata without requiring technical composition identifiers.

### Recomendar

`Recomendar` answers: "O que faz sentido comer neste slot/contexto?"

Normal users do not manually build a list of candidate rows. The server discovers the current eligible catalogue for the requested Person/Family context and returns ranked options. The browser may expose filters and context, but it does not choose authoritative nutrition evidence or recreate eligibility/ranking logic.

The existing manual-candidate recommendation form is an integration/development surface and must not remain the default meal UX.

## Meal-slot invariant

Normal planning must not create ambiguous duplicate active assignments for the same Person and logical meal slot.

The scheduling service must treat a Person's local date plus meal slot/type as occupied when that Person already participates in an active planned/prepared/served/completed meal for that slot, unless the operation explicitly replaces the prior assignment.

A shared Family meal occupies the slot once for every participating Person; it must not be represented as one independent duplicate event per participant.

This invariant is enforced server-side. The frontend may prevent obvious conflicts early, but it is not the authority.

## Family preference score

Family preference scoring is a food/recipe preference signal, not a health score.

The v2 baseline will preserve the useful v1 semantics:

- each Person can rate a dish/recipe from 0 to 5 and optionally leave a note;
- the Family view exposes rating count, individual ratings and a derived Family score;
- meaningful disagreement can be surfaced explicitly instead of being hidden by a simple average;
- preference scoring is an explainable ranking signal only.

Family preference must never bypass:

1. hard adverse-reaction/safety rules;
2. mandatory nutrition constraints;
3. required nutrition evidence rules.

It participates only after eligibility is established, alongside other explainable heuristics such as recency, repetition, meal suitability, practicality and dietary balance.

The exact persisted v2 rating model and scoring formula are implemented and versioned in a dedicated domain increment; v1 behavior is a compatibility target for product semantics, not a code dependency.

## Weekly planning semantics

Weekly planning uses a preview/apply workflow:

1. choose date range, participants and meal types (for example dinners only);
2. preserve existing/locked slots by default;
3. generate one suggestion per free logical slot;
4. show the suggestion, Family preference score, key reasons and any conflicts/missing evidence;
5. allow keep, replace or skip per slot;
6. apply the reviewed plan transactionally.

The planner should consider the whole requested horizon so it can reduce repetition and balance categories/proteins across the week rather than recommending each day independently.

## Consequences

Positive:

- the meal area matches normal user intent instead of exposing the integration test workflow;
- one shared dinner is visually and semantically one Family event;
- the user can plan a whole week without repeatedly invoking single-meal recommendation;
- the full dish catalogue and Family taste signal remain visible;
- v1's useful planning ideas are preserved while v2 keeps its stronger safety/provenance architecture.

Trade-offs:

- additional read/write APIs are required for date-range plans and slot-safe edits;
- the current recommendation endpoint needs a higher-level whole-catalog orchestration path;
- Family recipe ratings need explicit v2 persistence/versioning instead of relying only on generic like/dislike preferences;
- schedule conflict handling becomes a server domain responsibility.

## Related documents

- `docs/ux/family-meals-planning.md`
- `docs/ux/frontend-information-architecture.md`
- `docs/decisions/ADR-034-family-first-progressive-disclosure-web-navigation.md`
- `docs/decisions/ADR-007-development-workflow-and-ci.md`
