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

The visible application follows ADR-034.

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

`Refeições` now opens a lightweight Family meal map rather than the recommendation form directly.

Secondary navigation:

```text
Hoje
Semana
Recomendar
```

`Hoje` shows the active Family meals for the Family-local dashboard date. `Semana` shows the current Monday-to-Sunday Family-local week as seven readable vertical day sections, including explicit empty days.

Both views use:

```text
GET /api/families/{family_id}/meals?start_date=YYYY-MM-DD&days=N
```

The server owns Family-timezone boundaries and active-meal filtering. Shared meals appear once with participant names; Person-specific portions remain a later meal-detail drill-down.

`Recomendar` contains the existing practical recommendation vertical slice. The shell supplies the active Family context, so the planner does not ask for the Family UUID again. It still uses server planning bootstrap for current DailyNutritionState/composition evidence and the backend remains authoritative for safety, eligibility and ranking.

The Family Home `Planear refeição` action opens `Recomendar` directly, while selecting the primary `Refeições` destination starts at `Hoje`.

See `docs/ux/family-meals-today-week.md` and `docs/domain/family-meals-read-model.md`.

### Pessoas

`Pessoas` shows the Family member list. Selecting a member opens the first Person drill-down.

The Person view has secondary navigation:

```text
Visão geral
Nutrição
Atividade
Saúde
Histórico
Perfil
```

`Visão geral` is implemented and remains intentionally light. It presents current-day energy, activity, weight/trend, sleep and that Person's current-day meals from the Family dashboard read model. Missing evidence stays explicit.

The other secondary destinations are visible placeholders for future focused slices; they do not fabricate analytics or derive unsupported data in the browser.

See `docs/ux/person-overview.md`.

### Casa and Mais

`Casa` is an intentional placeholder for pantry/shopping.

`Mais` currently contains language, appearance and development Family-context controls. Authentication and real Family authorization are still pending.

See `docs/ux/family-home-shell.md`, `docs/ux/frontend-information-architecture.md`, `docs/ux/person-overview.md`, `docs/ux/family-meals-today-week.md` and ADR-034.

## Dependency locking

Direct dependency versions are pinned but an npm lockfile is not yet committed. Local and CI validation therefore use `npm install --no-package-lock`. A committed lockfile and `npm ci` are required before production deployment and should be added in a focused dependency-management hardening increment.
