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
2. **Refeições** — family meal map, today/week, recommendations and shared meals;
3. **Pessoas** — direct access to each person's overview and detail screens;
4. **Casa** — pantry and later shopping-list workflows;
5. **Mais** — family settings, integrations, appearance/language and administration.

Desktop uses a compact persistent side navigation. Mobile uses a compact bottom navigation for the same primary destinations, with lower-frequency actions inside `Mais`.

The navigation does not expand into a large tree permanently. Secondary navigation appears only after entering a Person or a specific workflow.

## Family home

The Home answers:

> Como está a família hoje?

It contains only three lightweight areas.

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

Cancelled and replaced meals do not clutter the normal Home agenda.

### 3. One next action

At most one prominent next action should be emphasized, for example:

- plan the next meal;
- review dinner;
- complete missing profile information.

The current Home uses `Planear refeição` as an explicit action into the recommendation subflow rather than trying to infer the next best action automatically.

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

The overview is intentionally compact. It shows today's most useful values and may later add one primary trend visualization when an authoritative historical read model exists. Detailed charts belong in the dedicated sections.

The implemented overview summarizes:

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
├── Recomendar
└── Refeição
    ├── resumo familiar
    ├── participantes
    ├── porções individuais
    ├── explicação
    └── alternativas / alterar
```

Entering the primary `Refeições` destination starts at `Hoje`. The Family Home `Planear refeição` action opens `Recomendar` directly because the user has already expressed recommendation/planning intent.

`Hoje` is a chronological Family-local agenda. `Semana` uses a Monday-to-Sunday vertical sequence of day sections rather than a dense seven-column calendar. Empty days stay explicit.

A shared meal is displayed once at family level. A later meal-detail drill-down will expose individual portions and Person-specific nutrition/safety outcomes already represented in the backend model.

The calendar views use a dedicated server read model so the browser does not decide local-day boundaries or reconstruct participants through request fan-out.

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
- weekly meals use vertical day sections rather than forcing a seven-column layout;
- detail pages can use two columns only where the content remains simple.

Mobile:

- bottom primary navigation;
- single-column screens;
- horizontal card carousels should be avoided for essential information;
- detail is reached by tapping rows/cards rather than expanding large accordions in place;
- meal-day sections remain vertically readable without a separate mobile information architecture.

Tablet follows the same information architecture and chooses side or bottom navigation based on available width.

## Data-authority boundary

The browser presents server evidence. It must not:

- choose which historical state/composition version is authoritative;
- infer medical meaning from raw health measurements;
- reproduce hard nutrition/safety rules;
- compute an aggregate family health score without an explicit domain definition;
- treat missing data as negative or zero;
- decide which UTC MealEvents belong to a Family-local calendar day.

Family Home and Family Meals use compact server read models so the browser does not need many requests or cross-domain/timezone aggregation logic.

## Implementation sequence and status

1. Family Home read model/API — integrated.
2. Application shell and primary navigation — integrated.
3. Family Home visual implementation — integrated.
4. Person overview — integrated.
5. Family meals today/week — current focused increment.
6. Meal drill-down with person-specific portions — next.
7. Person Nutrition/Activity/Health/History screens.
8. Profile/goals/constraints/preferences screens.
9. Pantry and shopping workflows.

Every increment remains usable on its own and keeps existing recommendation functionality reachable while the navigation evolves.
