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

A new local database is intentionally empty. Create the explicit development-only demo data with:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\api
python -m app.demo_seed
```

The command is idempotent and never runs automatically at API/web startup.

The Vite development shell defaults to the fixed demo Family ID when no Family has previously been selected in the browser. This is only a convenience for local development: it does not seed the database, and production builds do not receive that default.

## Validation

```powershell
npm run test
npm run build
```

`npm run build` performs a strict TypeScript check before the production Vite build.

## Family-first application shell

The visible application now follows ADR-034 rather than opening directly on the recommendation form.

Primary navigation:

```text
Início
Refeições
Pessoas
Casa
Mais
```

Desktop uses a compact left sidebar. Mobile uses bottom navigation.

### Início

`Início` uses:

```text
GET /api/families/{family_id}/dashboard
```

It shows a lightweight Family overview:

- one compact card per Person;
- current-day nutrition evidence when available;
- steps, weight/trend and sleep when available;
- explicit missing-data states;
- current Family meals for the day;
- one prominent action to plan a meal.

It does not calculate a Family health score or replace missing evidence with zero.

### Refeições

The practical recommendation vertical slice remains fully reachable under `Refeições`.

The shell supplies the active Family context, so the planner no longer asks for the Family UUID again. It still uses server planning bootstrap for current DailyNutritionState/composition evidence and the backend remains authoritative for safety, eligibility and ranking.

### Pessoas, Casa and Mais

`Pessoas` exposes the first member-selection surface; detailed Person overview is the next drill-down increment.

`Casa` is an intentional placeholder for pantry/shopping.

`Mais` currently contains language, appearance and development Family-context controls. Authentication and real Family authorization are still pending.

See `docs/ux/family-home-shell.md`, `docs/ux/frontend-information-architecture.md` and ADR-034.

## Dependency locking

Direct dependency versions are pinned but an npm lockfile is not yet committed. Local and CI validation therefore use `npm install --no-package-lock`. A committed lockfile and `npm ci` are required before production deployment and should be added in a focused dependency-management hardening increment.
