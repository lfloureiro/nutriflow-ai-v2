# Family meal detail

## Question answered

The meal-detail screen answers one focused question:

> Qual é a refeição e qual é a porção de cada pessoa?

It is a drill-down from `Refeições > Hoje` or `Refeições > Semana`, not another permanent top-level or secondary-navigation tab.

## Entry and exit

A Family meal remains one row in the daily/weekly meal map. Selecting that row opens the dedicated `Refeição` screen.

The detail screen provides a clear `Voltar às refeições` action that returns to the previous Today/Week context.

## Screen structure

The screen stays deliberately light:

1. **Meal summary**
   - title or meal type;
   - Family-local date/time;
   - optional location;
   - persisted MealEvent status.

2. **Individual portions**
   - one vertical card per persisted MealParticipant;
   - Person display name and participant status;
   - the Person's persisted Serving rows;
   - item name plus current concise quantity/energy evidence.

No Family-level nutrition dashboard, recommendation form or analytics grid is embedded in this screen.

## Serving evidence presentation

The API returns the persisted planned, served and consumed lifecycle fields independently.

For concise display, the web selects the most realized available evidence in this order:

```text
consumed -> served -> planned
```

This is only a presentation choice. The browser does not calculate a new portion, sum nutrition, infer consumption or modify persisted evidence.

If a participant has no Serving rows, the UI states that no portion is recorded rather than borrowing another Person's portion or treating it as zero.

## Shared-meal semantics

The shared MealEvent is not duplicated per Person. The detail screen preserves the domain structure:

```text
MealEvent
  -> MealParticipant (Person A)
       -> Serving(s) for Person A
  -> MealParticipant (Person B)
       -> Serving(s) for Person B
```

This means two people can eat the same dish with different quantities and energy evidence while the Family still sees a single shared meal.

## Scope of this increment

Implemented now:

- open a meal row into a focused detail screen;
- server-authoritative Family-scoped detail endpoint;
- persisted participant and Serving evidence;
- Person-specific quantity/energy display;
- explicit missing-Serving state;
- pt-PT/en copy;
- responsive single-column behavior.

Intentionally deferred:

- detailed recommendation explanation;
- alternatives and replacement/edit commands;
- nutrient-component breakdowns;
- aggregate meal nutrition summaries;
- safety-result rendering;
- URL/deep-link routing.

Those features should be introduced only when their own authoritative read/command semantics are defined, rather than making this first detail screen dense.

## Responsive behavior

Desktop and tablet keep a readable maximum content width and use vertically stacked participant cards.

Mobile remains single-column. Serving values wrap below the item when necessary; no horizontal participant table or seven-column layout is introduced.

## Data authority

The detail screen displays the result of:

```text
GET /api/families/{family_id}/meals/{meal_event_id}
```

The browser does not determine Serving ownership, cross-Family access, nutrition calculation or lifecycle state. Missing data remains missing.
