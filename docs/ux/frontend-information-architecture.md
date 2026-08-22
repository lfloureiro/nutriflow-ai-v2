# Frontend information architecture

## Principle

NutriFlow uses progressive disclosure: lightweight orientation screens lead to focused operational/detail screens. “Lightweight” means one primary task per screen; it does not mean hiding core planning functionality.

Family Home remains compact. A dedicated weekly planner may be denser because planning the week is its one job.

## Current primary shell

The currently integrated shell remains:

1. **Início** — Family orientation for today;
2. **Refeições** — current Today/Week read views and recommendation flow;
3. **Pessoas** — Person list and overview;
4. **Casa** — household operational workflows;
5. **Mais** — settings/integrations/family administration.

This shell will evolve as the operational meal-planning workflow becomes concrete. Do not treat the current five labels as immutable product ontology.

## Revised operational hierarchy

The product must make these destinations explicit and easy to reach:

```text
Plano
Receitas
Ingredientes
Despensa
Compras
Pessoas
```

On desktop these may become direct side-navigation destinations. On mobile they may be grouped behind a compact household/menu destination when five bottom-nav items are preferable. The information architecture is shared even when the navigation surface differs by viewport.

## Family Home

Home answers:

> Como está a família hoje?

It remains an orientation dashboard with:

- compact member cards;
- a short current-day meal summary;
- at most one prominent next action.

Home does not become the recipe editor, weekly planner, pantry manager or analytics warehouse.

## Ingredient catalogue

The first operational household workflow is now:

```text
Casa
  -> Ingredientes
       -> Lista / pesquisa
       -> Novo ingrediente
       -> Editar ingrediente
```

The list shows only identity and a compact latest nutrition summary. The editor contains descriptive data plus the manual composition fields needed by recipes.

Nutrition history/version identifiers remain backend evidence and are not shown as normal UI clutter.

## Recipes

The next workflow is:

```text
Receitas
  -> Lista / pesquisa
  -> Receita
       -> Identificação
       -> Ingredientes
       -> Rendimento / doses
       -> Preparação
       -> Nutrição calculada
       -> Preferências / ratings
```

Adding/editing ingredients belongs to the recipe editor rather than the weekly planner.

## Family planner

The existing `Hoje`/`Semana` views are useful read orientation but are not the final planner.

The planner must expose four fixed normal meal slots per day:

```text
Pequeno-almoço
Almoço
Lanche
Jantar
```

Each slot remains visible even when empty and supports add/change/remove/replace actions.

Desktop may use a compact planning grid or structured week layout. Mobile should use one day at a time or vertical day sections while preserving the same four-slot model.

A shared meal is represented once at Family level, then opens Person-specific participants/portions as needed.

## Person drill-down

Person information remains:

```text
Pessoa
├── Visão geral
├── Nutrição
├── Atividade
├── Saúde
├── Histórico
└── Perfil
```

The overview remains compact. Detailed analytics stay in the dedicated sections, but their implementation is intentionally behind the core Ingredients -> Recipes -> Planner -> Pantry -> Shopping sequence.

## Pantry and shopping

Household flow:

```text
Despensa
  -> stock atual / validade / quantidade

Plano + Receitas
  -> ingredientes necessários
  -> menos stock utilizável
  -> Compras
       -> lista durável
       -> ajustes manuais
       -> comprado / por comprar
```

## Data-authority boundary

The browser may collect user input and present server evidence. It must not:

- choose authoritative historical composition/state versions independently;
- recalculate recipe/Serving nutrition using ad-hoc browser rules;
- guess unsafe unit/density conversions;
- reproduce hard safety/nutrition eligibility logic;
- convert missing evidence into zero;
- infer medical meaning from health observations.

## Density rules

- Home: compact; normally zero or one small chart.
- Person overview: compact; at most one primary chart.
- Ingredients list: compact rows; edit on a separate screen.
- Recipe editor: focused multi-section form; no unrelated dashboard widgets.
- Weekly planner: allowed more density because the grid/slots are the primary task.
- Pantry/Shopping: task-oriented lists rather than dashboards.

## Responsive behavior

Desktop:

- persistent compact side navigation;
- readable maximum content width for forms/details;
- planner may use wider structured layout where useful.

Mobile:

- compact bottom navigation or household submenu;
- single-column editors;
- daily/vertical planner presentation;
- essential actions reached by tapping rows rather than expanding dense accordions.

## Implementation sequence

1. Family Home/shell/Person overview — integrated.
2. Family Meals Today/Week read views — integrated.
3. Ingredient catalogue — current branch.
4. Recipe CRUD + ingredient editor + deterministic recipe composition.
5. Four fixed meal types and read/write Family planner model.
6. Planner UI with add/change/remove/recipe selection.
7. Person-specific planned portions.
8. Recipe ratings/preferences and ranking integration.
9. Pantry UI.
10. Durable shopping-list workflow.
11. Resume secondary analytics/detail expansion.
