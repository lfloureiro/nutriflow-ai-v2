# Family meals: Hoje and Semana

## Question answered by the screen

The primary `Refeições` destination answers:

> O que está planeado para a família?

It should not open directly into a large recommendation form. The meal calendar is the orientation layer; recommendation is an explicit subflow reached only when the user wants help choosing a meal.

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

The first implementation uses a vertical list of seven day sections rather than a dense spreadsheet/calendar grid. This choice follows the product preference for more focused, readable screens over high-density dashboards and remains usable on narrow mobile screens.

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

## Shared meals

A shared meal is shown once in the Family calendar with its participant names.

This screen does not yet expose Person-specific portions. Selecting a Family meal and drilling into individual portions/outcomes is the next meal-detail increment.

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

## Implementation checkpoint

The focused branch implementation, tests and documentation are complete. The branch must still pass the full local API/Web validation gates and browser smoke test on its exact head before a pull request is opened.
