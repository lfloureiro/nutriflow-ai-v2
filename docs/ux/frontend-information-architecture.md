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

The initial product-level navigation is:

1. **Início** — family overview for today;
2. **Refeições** — family meal map, today/week, recommendations and shared meals;
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

Meals remain a primary family workflow rather than becoming the Home itself.

```text
Refeições
├── Hoje
├── Semana
├── Recomendar refeição
└── Refeição
    ├── resumo familiar
    ├── participantes
    ├── porções individuais
    ├── explicação
    └── alternativas / alterar
```

A shared meal is displayed once at family level, while drill-down exposes the individual portions and Person-specific nutrition/safety outcomes that already exist in the backend model.

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

For Home, the server should expose a compact family read model so the browser does not need many requests or cross-domain aggregation logic.

## Initial implementation sequence

1. Family Home read model/API.
2. Application shell and primary navigation.
3. Family Home visual implementation.
4. Person overview.
5. Family meals today/week.
6. Meal drill-down with person-specific portions.
7. Person Nutrition/Activity/Health/History screens.
8. Profile/goals/constraints/preferences screens.
9. Pantry and shopping workflows.

Every increment should remain usable on its own and keep existing recommendation functionality reachable while the navigation is reorganized.
