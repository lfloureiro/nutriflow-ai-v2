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

## Dependency locking

Direct dependency versions are pinned but an npm lockfile is not yet committed. Local and CI validation therefore use `npm install --no-package-lock`. A committed lockfile and `npm ci` are required before production deployment and should be added in a focused dependency-management hardening increment.
