# Meal calendar navigation

## Decision

`Refeições` is a meal map first, not a recommendation form and not a long agenda list.

The default Family meal surface provides three explicit time scales:

```text
Dia | Semana | Mês
```

The same time-scale control is reused inside an individual Person under `Pessoas > {Person} > Refeições`, filtered to that Person.

This restores temporal orientation as a first-class part of the product and keeps meal planning separate from health/activity overview screens.

## Global information architecture

```text
Início
Refeições
Pessoas
Casa
Mais
```

### Início

Answers: `Como está a família hoje?`

Contains only a compact Family health/activity/nutrition overview plus a small indication of the next Family meal. It must not become the full meal calendar.

### Refeições

Answers: `O que vai comer a família e quando?`

Default destination is the Family meal calendar.

Top-level controls:

```text
< período anterior   Hoje   período seguinte
Dia | Semana | Mês
                                     [Planear refeição]
```

`Planear refeição` opens the existing recommendation/planning flow as a dedicated sub-flow. The recommendation form must not replace the calendar as the section landing page.

### Pessoas

The primary `Pessoas` destination is the Family member list/grid.

Selecting a Person opens a clearly identified Person space with persistent Person header and secondary navigation:

```text
Visão geral | Refeições | Nutrição | Atividade | Saúde | Histórico | Perfil
```

A Person page must never visually read as a generic Family meal list.

## Family meal calendar

### Semana — default desktop view

The weekly Family map is a compact matrix.

Columns are days. Rows are:

```text
Família
Pessoa A
Pessoa B
Pessoa C
...
```

The `Família` row holds genuinely shared MealEvents. Individual rows hold Person-specific meals.

Each cell contains compact meal chips rather than large cards:

```text
08:00  Pequeno-almoço
13:00  Massa à bolonhesa
20:00  Jantar em família
```

Shared meals appear once in the Family row, with compact participant indication. They are not duplicated once per Person merely to fill the matrix.

Selecting a meal opens its detail screen with status, participants and eventually Person-specific portions.

### Dia

The day view keeps Family/Person rows and uses meal periods as compact columns when practical:

```text
              Pequeno-almoço   Almoço   Lanche   Jantar
Família
Pessoa A
Pessoa B
Pessoa C
```

Exact times remain visible inside meal chips. Additional/off-schedule meals may appear in the appropriate period or an `Outras` group.

On narrow screens the same data becomes a compact chronological day list grouped by `Família` and Person; it must not render a horizontally unusable desktop matrix.

### Mês

Month view is intentionally summary-level. It uses a normal month grid and does not attempt to render every Person meal in every day cell.

Each day shows compact counts/signals such as:

```text
3 refeições
1 familiar
```

Selecting a day drills into `Dia` for that date.

This is progressive disclosure: month answers where activity exists; day/week answer what the meals are.

## Person meal calendar

`Pessoas > {Person} > Refeições` reuses the same temporal model:

```text
Dia | Semana | Mês
```

It is filtered to meals in which that Person participates.

Weekly Person view uses days as columns and compact meal chips within each day. It does not repeat the Family/Person row dimension because scope is already one Person.

Shared Family meals remain visible in the Person calendar when that Person participates, with a `Família` marker.

## Density rules

- Prefer calendar cells, compact rows and chips over large repeated cards.
- A repeated meal list must not consume the entire content width with one card per meal.
- Keep the global shell stable while drill-down content changes.
- Person identity must remain visible while inside Person detail.
- `Dia | Semana | Mês` remains visible on meal-calendar screens.
- Recommender/planner is an action/sub-flow, not the meal section home.
- Missing data is explicit; UI does not invent meals, nutrition or status.

## Current screenshot feedback addressed

The previous Person overview allowed today's meals to dominate the selected Person screen as large stacked cards. This made `Pessoas` visually resemble a generic meal feed, hid temporal orientation and made accumulated development MealEvents look especially noisy.

The corrective direction is:

1. keep `Visão geral` focused on Person summary metrics;
2. move the complete Person meal history/map to the explicit `Refeições` Person tab;
3. make global `Refeições` land on the Family calendar;
4. restore `Dia | Semana | Mês` in both Family and Person meal contexts;
5. use compact calendar presentation instead of full-width meal cards.
