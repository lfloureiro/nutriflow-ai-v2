# Family meals: Hoje and Semana

## Question answered by the screen

The primary `Refeições` destination answers:

> O que está planeado para a família?

It does not open directly into a large recommendation form. The meal calendar is the orientation layer; recommendation is an explicit subflow reached only when the user wants help choosing a meal.

## Secondary navigation

```text
Refeições
├── Hoje
├── Semana
└── Recomendar
```

Entering `Refeições` from primary navigation defaults to `Hoje`.

The prominent `Planear refeição` action on Family Home opens `Recomendar` directly because that action already expresses planning intent.

## Hoje

`Hoje` is a chronological Family agenda for the Family-local dashboard date.

Each row shows only:

- local time;
- meal title/type;
- participants;
- optional location;
- current meal state.

The view remains useful with zero meals: an explicit empty state is preferable to showing planner controls automatically.

## Semana

`Semana` shows the current Family-local Monday-to-Sunday calendar week.

The implementation uses a vertical list of seven day sections rather than a dense spreadsheet/calendar grid. This follows the product preference for focused, readable screens over high-density dashboards and remains usable on narrow mobile screens.

Every day is visible even when empty. Days with meals list the same compact rows used by `Hoje`.

This is a planning map, not an analytics screen. It does not add calorie charts, nutrient tables or recommendation explanations to the week view.

## Recomendar

`Recomendar` contains the existing practical recommendation vertical slice.

The recommendation form is deliberately separated from `Hoje` and `Semana` so users can inspect the Family plan without first entering meal-generation context.

Existing server-authoritative behavior remains unchanged:

- current DailyNutritionState is selected through planning bootstrap;
- valid composition snapshots are selected by the server;
- hard safety/mandatory rules run before ranking;
- commercial availability cannot override safety;
- accepted options materialize through the decision API.

## Shared meals and drill-down

A shared meal is shown once in the Family calendar with its participant names.

Selecting a row now opens the dedicated Family meal-detail drill-down. Person-specific portions remain outside the calendar itself, preserving the low-density Today/Week views.

See `docs/ux/family-meal-detail.md` for the focused detail-screen semantics.

## Responsive behavior

Desktop and tablet:

- readable content width;
- compact day cards;
- no full-width seven-column calendar required.

Mobile:

- single-column day sections;
- meal metadata wraps below the title;
- secondary navigation remains horizontally compact;
- primary application navigation remains the existing bottom bar.

## Missing/empty data

No meal for a day means exactly that: no active planned/prepared/served/completed MealEvent was returned for that Family-local day.

The UI does not infer meals, carry forward previous plans or create placeholders that look like real meal state.

## Data source

Both views use:

```text
GET /api/families/{family_id}/meals?start_date=YYYY-MM-DD&days=N
```

See `docs/domain/family-meals-read-model.md` for authority, timezone and filtering semantics.

## Integrated checkpoint

`Hoje`, `Semana` and `Recomendar` were locally validated, API/Web CI-green on the exact branch head, and squash-merged in PR #33.

Integrated main checkpoint:

```text
e0bdd8a9c8cc40f58ab67f14727ab134ac2156dc
```

The current follow-up increment adds the separate shared-meal detail screen without increasing the density of these calendar views.
