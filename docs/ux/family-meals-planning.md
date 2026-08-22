# Family meals planning UX

## Purpose

`Refeições` is a Family workflow. It should help answer four different questions without combining them into one dense screen:

```text
Hoje        O que vamos comer hoje?
Semana      O que está planeado para os próximos dias?
Pratos      Que refeições/receitas temos disponíveis e quanto gosta a família delas?
Recomendar  O que faz sentido escolher para um slot específico?
```

The current technical recommendation form is not the target product experience.

## Secondary navigation

```text
Refeições
[ Hoje ] [ Semana ] [ Pratos ] [ Recomendar ]
```

On mobile the same destinations remain available as a compact horizontally scrollable tab row or equivalent focused secondary navigation. They must not become four full sections stacked on one page.

## Hoje

The Today screen is a chronological Family meal map.

Example:

```text
Hoje · sábado 22 agosto

08:00  Pequeno-almoço
       Torradas, leite, iogurte
       Luís · Patrícia · Rui · Inês
       Concluído

13:00  Almoço
       Luís: Massa à bolonhesa
       Patrícia: Salada de grão

20:00  Jantar em família
       Frango com arroz e legumes
       4 pessoas
       Planeado
```

Rules:

- one shared MealEvent appears once;
- Person-specific alternatives can appear inside the same slot without pretending they are separate Family meals;
- tapping a slot opens meal detail;
- the meal detail owns Person portions, ingredients/composition, explanations and alternatives;
- duplicate active assignments for the same Person/meal slot are rejected server-side;
- replacing a meal is explicit rather than silently adding another event at the same time.

Primary actions:

- `Adicionar refeição` when a slot is empty;
- `Alterar`/`Substituir` from meal detail;
- `Recomendar` for a selected free/existing slot.

## Semana

The Week screen defaults to the current local Family week and should remain light.

Desktop can show seven compact day columns/rows, but each cell only needs the meal title and a small state marker. Mobile shows one day at a time with previous/next day navigation.

The default view may focus on dinners because they are commonly shared Family decisions; the user can switch meal types.

Example:

```text
Semana 17–23 ago                        [ Planear semana ]

Seg  Jantar  Salmão com batata e salada      4,6 ★
Ter  Jantar  Frango com arroz e legumes       4,3 ★
Qua  Jantar  —                                +
Qui  Jantar  Vaca com molho de ostras         3,8 ★
Sex  Jantar  —                                +
Sáb  Jantar  Pizza                            3,1 ★
Dom  Jantar  —                                +
```

### Planear semana

`Planear semana` is a focused multi-step flow rather than a large parameter panel.

Step 1 — Scope

- date range;
- Family members;
- meal types (`Jantar` selected by default when entered from a dinner-focused week view).

Step 2 — Practical rules

- time available/cooking context where relevant;
- meals/days already fixed remain locked by default;
- optional balance rule such as meat/fish/vegetarian distribution.

Step 3 — Preview

One suggestion per free slot, with:

- dish name;
- Family preference score;
- short reason(s): preference, recency, variety, nutrition/practical fit;
- explicit unavailable/excluded state when hard rules prevent a valid suggestion.

Each suggestion supports:

- keep;
- replace;
- skip.

Step 4 — Confirm

Apply the reviewed set together. Existing locked slots are preserved.

## Pratos

`Pratos` is the complete Family meal/recipe catalogue used by planning and recommendation.

The default list for the Family should be useful without filters. Filters are secondary.

Each row/card can show:

```text
Frango com arroz e legumes
Jantar · Carne
Família 4,5 ★ · 4 avaliações
Última vez: há 8 dias
```

Useful filters/sorts:

- suitable for dinner/lunch/etc.;
- Family score;
- recently/long ago used;
- category/protein;
- preparation time / practical availability when known;
- favorites / not yet rated.

Tapping a dish opens its detail and the per-Person rating surface.

### Family ratings

Each Person can give a 0–5 rating and optional note. The catalogue shows the derived Family preference score and number of ratings.

A detail view can show:

```text
Família     4,4 ★
Luís        5 ★
Patrícia    4 ★
Rui         5 ★
Inês        2 ★   ⚠ preferência diferente
```

This is a preference/taste signal only. It is never presented as nutritional or health quality.

## Recomendar

The recommendation screen starts from intent, not from technical candidates.

Normal flow:

```text
Recomendar

Para quem?        Família / pessoas selecionadas
Quando?           Hoje · Jantar · 20:00
Onde?             Casa
Tempo disponível  30 min

[ Recomendar ]
```

The server then evaluates the current catalogue and returns ranked options.

Result cards should emphasize:

- dish name;
- Family preference score when available;
- nutrition/practical fit summary;
- concise explainability;
- whether the result is eligible.

Hard-excluded items should not dominate the normal list. They can live under `Ver opções excluídas` with their explicit reason.

Selecting an eligible recommendation offers one clear action:

- `Usar neste jantar` for an empty slot;
- `Substituir jantar atual` for an occupied slot.

The UI must not allow an ordinary acceptance to create a second active meal assignment for the same Person/slot.

## Relationship to v1

Useful v1 behavior to preserve semantically in standalone v2:

- per-member 0–5 recipe ratings and notes;
- Family score with disagreement visibility rather than only a naive average;
- whole-recipe catalogue visible to the Family;
- weekly auto-plan preview before apply;
- occupied slots preserved by default;
- scoring incorporates Family acceptance, recency/repetition and category/protein balance.

v2 extends those ideas with stronger Person-specific safety, nutrition-state, provenance and shared-meal portion semantics. Hard safety/nutrition rules always run before preference or planning heuristics.

## Density rules

- Today shows the day's meal map, not recipe analytics.
- Week shows the plan, not every nutritional metric.
- Dishes shows catalogue/preference information, not the weekly calendar.
- Recommend shows ranked choices for one planning intent, not the whole week.
- Detailed nutrition, portions and explanation are drill-down screens.

This separation is deliberate: more focused screens are preferred over one overloaded meal-planning dashboard.
