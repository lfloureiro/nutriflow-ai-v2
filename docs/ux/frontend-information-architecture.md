# Frontend information architecture

## Product navigation principle

NutriFlow should prefer more focused screens over dense dashboards. A screen should answer one primary question and offer clear drill-down paths rather than presenting every available metric at once.

The frontend therefore uses progressive disclosure:

- family first for orientation;
- person drill-down for individual detail;
- meals as a parallel family workflow;
- health, activity and nutrition details on dedicated screens;
- technical identifiers and backend evidence remain hidden from normal users;
- missing data is shown explicitly rather than inferred or filled with invented status.

## Primary navigation

The product-level navigation is:

1. **Início** — family overview for today;
2. **Refeições** — family meal map, week planning, dish catalogue and recommendations;
3. **Pessoas** — direct access to each person's overview and detail screens;
4. **Casa** — pantry and later shopping-list workflows;
5. **Mais** — family settings, integrations, appearance/language and administration.

Desktop should use a compact persistent side navigation. Mobile should use a compact bottom navigation for the same primary destinations, with lower-frequency actions inside `Mais`.

The navigation should not expand into a large tree permanently. Secondary navigation appears only after entering a Person or a specific workflow.

## Family home

The Home answers:

> Como está a família hoje?

It should contain only three lightweight areas.

### 1. Family members

One compact card per Person, showing a small selection of available indicators such as:

- nutrition progress/evidence;
- activity/steps when available;
- weight and short trend when available;
- sleep when available.

The card is a navigation surface, not a medical scorecard. It must not manufacture a single "health score" from unrelated inputs unless a future explicit domain decision defines such a metric.

Clicking/tapping a Person opens that Person's overview.

### 2. Today

A small chronological list of today's current meal events:

- meal type/title;
- local time;
- whether it is shared and by whom;
- current state such as planned/completed.

Cancelled and replaced meals should not clutter the normal Home agenda.

### 3. One next action

At most one prominent next action should be emphasized, for example:

- plan the next meal;
- review dinner;
- complete missing profile information.

The first implementation does not need to infer this action automatically.

## Person drill-down

Person information architecture:

```text
Pessoa
├── Visão geral
├── Nutrição
├── Atividade
├── Saúde
├── Histórico
└── Perfil
    ├── Objetivos
    ├── Restrições
    ├── Preferências
    └── Integrações relevantes
```

### Person overview

The overview is intentionally compact. It should show today's most useful values plus one primary trend visualization. Detailed charts belong in the dedicated sections.

The overview can summarize:

- energy/nutrition state;
- activity state;
- latest weight/trend;
- sleep/recovery evidence when available;
- today's meals for that Person.

### Detailed sections

Each detailed section answers one question:

- **Nutrição:** how intake/planning compares with current targets;
- **Atividade:** movement, active energy, training/activity history;
- **Saúde:** body/health observations and connected-source evidence within the wellness boundary;
- **Histórico:** chronological changes and meal/nutrition history;
- **Perfil:** relatively stable user-controlled facts, goals, constraints and preferences.

## Meals information architecture

Meals remain a primary Family workflow rather than becoming the Home itself. The initial recommendation form was an integration slice, not the target meal UX.

```text
Refeições
├── Hoje
├── Semana
├── Pratos
├── Recomendar
└── Refeição
    ├── resumo familiar
    ├── participantes
    ├── porções individuais
    ├── explicação
    └── alternativas / alterar
```

### Hoje

Answers: **what is the Family eating today?**

Shows the chronological Family meal map. A shared meal is displayed once at Family level. Person-specific exceptions or portions are drill-down details rather than duplicate top-level events.

### Semana

Answers: **what is planned for this week?**

Shows the planning horizon with one logical slot per Family/Person meal assignment. It must support a focused `Planear semana` preview/apply flow that can fill several free slots together while preserving existing/locked meals by default.

### Pratos

Answers: **what meals/recipes can we choose from?**

Shows the complete usable dish/recipe catalogue with Family preference score, per-Person ratings, suitability and planning metadata. This keeps the catalogue visible instead of forcing users to discover dishes only through recommendation results.

### Recomendar

Answers: **what makes sense for this specific slot/context?**

The normal flow supplies Person/Family, slot and practical context; the server evaluates the current catalogue. Users do not manually assemble technical candidate rows. Hard safety/nutrition eligibility remains server-authoritative before preference/heuristic ranking.

The Family preference score is a taste/acceptance signal, not a health score.

### Meal detail

A shared MealEvent is shown once at Family level, while drill-down exposes individual portions and Person-specific nutrition/safety outcomes that already exist in the backend model.

Normal scheduling must not silently create duplicate active meal assignments for the same Person and logical meal slot. Replacing an occupied slot is explicit and server-enforced.

Detailed design: `docs/ux/family-meals-planning.md` and ADR-035.

## Charts

Charts are useful but should not dominate every screen.

Rules:

- Home should normally contain zero or one small trend chart, not a grid of analytics widgets;
- Person overview should contain at most one primary chart;
- detailed pages may contain more charts because the user explicitly entered an analytical context;
- charts must have a clear question/title and should not mix unrelated measures merely to save screen space;
- sparklines or compact trends are preferred inside Person cards when a numeric trend is actually available;
- absence of evidence renders as unavailable/unknown, never as zero.

## Responsive behaviour

Desktop:

- compact side navigation;
- content uses a readable maximum width rather than filling the whole monitor;
- member cards may form a small grid;
- detail pages can use two columns only where the content remains simple.

Mobile:

- bottom primary navigation;
- single-column screens;
- horizontal card carousels should be avoided for essential information;
- detail is reached by tapping rows/cards rather than expanding large accordions in place.

Tablet follows the same information architecture and chooses side or bottom navigation based on available width.

## Data-authority boundary

The browser presents server evidence. It must not:

- choose which historical state/composition version is authoritative;
- infer medical meaning from raw health measurements;
- reproduce hard nutrition/safety rules;
- compute an aggregate family health score without an explicit domain definition;
- treat missing data as negative or zero.

For Home, the server exposes a compact family read model so the browser does not need many requests or cross-domain aggregation logic.

For Meals, the server owns slot-conflict checks, whole-catalog eligibility/ranking, weekly plan generation and application semantics. The browser presents and edits intent; it does not reconstruct these rules.

## Implementation sequence

1. Family Home read model/API. **Done.**
2. Application shell and primary navigation. **Done.**
3. Family Home visual implementation. **Done.**
4. Person overview. **Done.**
5. Family Meals information architecture and slot-safe planning foundation.
6. `Hoje` + `Semana` read/write flows and weekly preview/apply planning.
7. `Pratos` catalogue + Family 0-5 preference scoring.
8. Whole-catalog `Recomendar` UX replacing the technical manual-candidate form.
9. Meal drill-down with Person-specific portions.
10. Person Nutrition/Activity/Health/History screens.
11. Profile/goals/constraints/preferences screens.
12. Pantry and shopping workflows.

Every increment should remain usable on its own and preserve the backend safety/provenance authority boundary.
