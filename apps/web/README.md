# NutriFlow AI web

React + TypeScript web application for NutriFlow AI v2.

## Local development

Run the FastAPI application on `127.0.0.1:8000`, then from this directory:

```powershell
npm install --no-package-lock --ignore-scripts
npm run dev
```

Vite serves the web app on `http://127.0.0.1:5173` and proxies `/api` requests to the local FastAPI server.

Set `VITE_API_BASE_URL` only when the API is hosted on a different origin. The default same-origin path is preferable for local development through the Vite proxy.

### Fresh database demo data

A new local database is intentionally empty. To create the explicit development-only demo Family, current daily nutrition state and six named meal candidates:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\api
python -m app.demo_seed
```

The command is idempotent and prints the Family ID to enter in the current pre-authentication web screen. It never runs automatically at application startup. See `docs/domain/development-demo-dataset.md` and ADR-033.

## Validation

```powershell
npm run test
npm run build
```

`npm run build` performs a strict TypeScript check before the production Vite build.

## Current vertical slice

The meal-planning flow uses the server planning-bootstrap endpoint rather than technical UUID entry. It supports:

- Family ID -> Person selection;
- automatic DailyNutritionState discovery for the selected Person and local meal instant;
- server-authoritative current FoodItem/Recipe composition discovery;
- human-readable candidate selection with reference serving and energy metadata;
- practical context (time, location, kitchen, available minutes and source kinds);
- practical recommendation generation;
- eligible/excluded result explanations;
- current commercial offer display;
- accept/reject decisions for eligible persisted options;
- Portuguese/English UI;
- Light/Dark/System appearance;
- responsive desktop/tablet/mobile layout.

Composition IDs remain internal to the typed API client. If the server reports no DailyNutritionState for the selected date, the UI shows that explicitly and does not guess a state.

Authentication and production household authorization context are not implemented yet, so Family ID remains a development entrypoint.

## Family-first product direction

The existing recommendation screen is an integration slice, not the final application Home.

The agreed primary navigation is:

```text
Início
Refeições
Pessoas
Casa
Mais
```

The application starts conceptually at Family level. `Início` is a lightweight view of how the Family is doing today, with compact Person cards and today's meal agenda. Person detail, health/activity/nutrition analytics and meal detail are reached through drill-down rather than expanding one large dashboard.

The browser client now has typed support for:

```text
GET /api/families/{family_id}/dashboard?on_date=YYYY-MM-DD
```

This endpoint is the read-model foundation for the future Family Home. It exposes current-day member health/nutrition evidence and current Family meals without inventing cross-domain scores or converting missing data to zero.

The visual application shell and Family Home are deliberately the next focused increments rather than being mixed into the read-model branch.

See `docs/ux/frontend-information-architecture.md` and ADR-034.

## Dependency locking

Direct dependency versions are pinned but an npm lockfile is not yet committed. Local and CI validation therefore use `npm install --no-package-lock`. A committed lockfile and `npm ci` are required before production deployment and should be added in a focused dependency-management hardening increment.
