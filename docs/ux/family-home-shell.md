# Family Home application shell

## Purpose

This vertical slice implements the first visible form of the family-first information architecture accepted in ADR-034. It replaces the developer-oriented recommendation screen as the application entry point while keeping recommendation functionality available under `Refeições`.

The shell is intentionally light. It does not attempt to implement every future destination in one increment.

## Primary navigation

The same five destinations are exposed on all screen sizes:

```text
Início
Refeições
Pessoas
Casa
Mais
```

Desktop uses a compact persistent left sidebar. Mobile uses a fixed bottom navigation. Navigation is implemented without adding a routing dependency yet because the current pre-authentication application remains a single client session; URL routing can be introduced when deep links and authenticated navigation require it.

## Development Family context

Authentication/authorization is still pending. Until that exists, the shell keeps one development Family context.

- the selected Family ID is stored in browser local storage after a successful dashboard load;
- local Vite development defaults to the fixed explicit demo Family ID when no stored value exists;
- this default does not create or seed data;
- production builds do not receive the demo default;
- `Mais` allows the development Family context to be cleared and changed.

The explicit `python -m app.demo_seed` command remains the only supported way to create demo data.

## Início

`Início` calls the server-authoritative Family dashboard read model and answers one question:

> Como está a família hoje?

It displays:

- the Family name and local dashboard date;
- one compact card per Person;
- nutrition consumed energy when current-day nutrition state exists;
- steps, weight trend direction and sleep when current-day health state exists;
- explicit `Sem dados` / `No data` for missing evidence;
- current-day Family MealEvents in chronological order;
- one prominent action to plan a meal.

No aggregate health score is calculated. No missing health or nutrition evidence is converted to zero.

Person cards navigate into `Pessoas`. The detailed Person overview is deliberately a later vertical slice.

## Refeições

The existing recommendation capability is retained and moved under `Refeições`.

The Family ID is no longer requested again inside the planner. The shell passes the active Family context and the planner loads Family members itself. It continues to use:

```text
GET  /api/persons/{person_id}/planning-bootstrap
POST /api/persons/{person_id}/meal-recommendations/practical
POST /api/recommendation-options/{option_id}/decision
```

The browser still does not choose authoritative DailyNutritionState or composition versions and does not reimplement eligibility/safety/ranking rules.

Returning to `Início` reloads the Family dashboard so an accepted planned meal can appear in the agenda.

## Pessoas

The first shell exposes the Family member list and selected-person state. It intentionally stops before implementing health/nutrition drill-down. This keeps the increment focused and makes the next vertical slice explicit.

## Casa and Mais

`Casa` is an intentional lightweight placeholder for pantry/shopping workflows.

`Mais` currently contains application language, appearance and development Family-context controls. Future integrations and Family administration belong here.

## Responsive density rules

The implementation preserves the agreed progressive-disclosure constraints:

- no chart grid on Family Home;
- no synthetic family health score;
- no horizontal essential-information carousel;
- member cards use at most four compact indicators;
- desktop content keeps a readable maximum width;
- mobile uses one-column content and bottom navigation;
- recommendation detail remains on the dedicated Meals screen rather than expanding Home.

## Known limitations

- Family context is not authorization; authentication is still mandatory before real multi-user use;
- the demo Family has limited health/activity evidence until the demo dataset is enriched;
- Person detail is not yet implemented;
- `Casa` is not yet functional;
- URL/deep-link routing is not introduced in this shell increment;
- Person-local wall-time entry in the recommendation planner retains the existing browser-timezone limitation.

## Related documents

- `docs/ux/frontend-information-architecture.md`
- `docs/domain/family-dashboard-read-model.md`
- `docs/decisions/ADR-034-family-first-progressive-disclosure-web-navigation.md`
- `docs/development-continuity.md`
