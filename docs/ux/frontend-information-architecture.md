# Frontend information architecture

## Principle

NutriFlow uses progressive disclosure: lightweight orientation screens lead to focused operational/detail screens. “Lightweight” means one primary task per screen; it does not mean hiding core planning functionality.

Family Home remains compact. A dedicated weekly planner may be denser because planning the week is its one job.

## Current primary shell

The shell remains:

1. **Início** — Family orientation for today;
2. **Refeições** — operational Family meal plan;
3. **Pessoas** — Person list and overview;
4. **Casa** — recipes, ingredients, pantry and shopping;
5. **Mais** — settings/integrations/family administration.

The compact five-destination shell avoids an overloaded mobile bottom bar while still exposing the operational hierarchy through focused secondary tabs.

## Operational hierarchy

```text
Refeições
  -> Hoje
  -> Semana
  -> Recomendar

Casa
  -> Receitas
  -> Ingredientes
  -> Despensa
  -> Compras

Pessoas
  -> Visão geral
  -> detailed nutrition/activity/health/history later
```

## Family Home

Home answers:

> Como está a família hoje?

It remains an orientation dashboard with compact member cards, short meal context and one prominent planning action. `Planear refeição` enters the operational plan instead of jumping directly into recommendation generation.

## Recipes and ingredients

`Casa` opens by default on **Receitas**, because Recipe is the reusable object the Family normally chooses when planning a meal.

```text
Casa
├── Receitas
│   ├── lista / pesquisa
│   ├── nova receita
│   └── editor
│       ├── identificação / preparação
│       ├── rendimento / doses
│       ├── ingredientes ordenados
│       └── nutrição calculada / problemas de evidência
└── Ingredientes
    ├── lista / pesquisa
    ├── novo ingrediente
    └── editor de composição
```

Ingredient and Recipe lists remain compact; editing happens on focused screens.

The browser never calculates Recipe nutrition. It presents the latest server-created RecipeCompositionSnapshot and explicit issues.

## Family planner

`Refeições` is the real planner rather than a read-only agenda.

Every day always contains exactly four slots:

```text
Pequeno-almoço
Almoço
Lanche
Jantar
```

Empty slots remain visible and provide an Add action. A planned meal can be opened to change Recipe, local time, location, Family participants and Person-specific quantities/units.

Removal cancels the planned MealEvent rather than erasing history. Prepared, served and completed events remain visible but are locked from planning edits.

`Hoje` and `Semana` use the same model. Desktop may show the four slots across the row where space allows; mobile stacks them vertically. There is no separate semantic mobile planner.

`Recomendar` preserves the existing recommendation workflow as a supporting tool. Recommendation should later feed a chosen result back into the same planner rather than remain a separate meal ontology.

## Shared meals and portions

One shared Recipe meal is one MealEvent. Participants are MealParticipant records and portions are Person-specific Servings.

The planner editor keeps portions optional: leaving quantity blank asks the server to derive the normal Recipe portion from yield/serving-count evidence. Explicit quantities remain Person-specific.

## Pantry

`Casa -> Despensa` is a task-oriented stock list/editor:

```text
Despensa
├── stock atual
├── novo lote
├── quantidade / unidade
├── localização
├── validade
└── retirar / reativar stock
```

The screen does not calculate meal requirements. It records household stock evidence that the server later uses when building shopping requirements.

## Shopping

`Casa -> Compras` closes the operational loop:

```text
Plano + Receitas
  -> requisitos agregados
  -> menos stock utilizável da Despensa
  -> Compras
       -> necessário / em stock / falta
       -> itens automáticos
       -> itens manuais
       -> comprado / por comprar
```

The user selects the planning interval and explicitly refreshes the list from the plan. This keeps the relationship between planner changes and shopping generation visible instead of silently mutating the list in the background.

Purchased items remain visible as checked items. Recording a purchase does not itself claim that pantry stock has changed; Pantry remains explicit observed household state.

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

Detailed analytics are intentionally behind the operational meal-planning sequence.

## Data-authority boundary

The browser may collect input and present server evidence. It must not:

- choose authoritative historical composition/state versions independently;
- recalculate Recipe/Serving nutrition with browser rules;
- aggregate authoritative shopping quantities itself;
- subtract pantry stock itself;
- guess unsafe unit/density conversions;
- reproduce hard safety/nutrition eligibility logic;
- convert missing evidence into zero;
- infer medical meaning from health observations.

## Density rules

- Home: compact; normally zero or one small chart.
- Person overview: compact; at most one primary chart.
- Ingredient/Recipe lists: compact rows.
- Recipe editor: focused multi-section form.
- Weekly planner: allowed more density because planning is its sole task.
- Pantry/Shopping: task-oriented lists rather than dashboards.

## Responsive behavior

Desktop:

- persistent compact side navigation;
- readable maximum content width for forms/details;
- four-slot planner can use wider structured rows;
- shopping requirements may use compact multi-column rows.

Mobile:

- compact bottom navigation;
- `Casa` secondary tabs wrap as needed;
- single-column editors;
- vertically stacked day/meal slots;
- pantry/shopping rows collapse to one column;
- essential actions reached by tapping rows rather than large inline expansions.

## Implementation sequence

1. Family Home/shell/Person overview — integrated.
2. Family Meals Today/Week orientation views — integrated.
3. **Core operational meal-planning foundation** — current large integration:
   - ingredients;
   - recipes;
   - deterministic Recipe nutrition;
   - fixed four meal types;
   - editable Today/Week planner;
   - Person-specific planned portions;
   - Pantry CRUD/UI;
   - planned-Recipe requirement aggregation;
   - quantity-aware pantry subtraction;
   - durable ShoppingList lifecycle/UI.
4. Recipe ratings/preferences + planning/recommendation ranking integration.
5. Resume secondary Person analytics/detail expansion.
