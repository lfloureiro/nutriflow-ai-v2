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

The first slice intentionally uses explicit persisted IDs because catalogue discovery and DailyNutritionState selection APIs are not yet exposed for the UI. It supports:

- Family ID -> Person selection;
- explicit DailyNutritionState and candidate composition IDs;
- practical context (time, location, kitchen, available minutes and source kinds);
- practical recommendation generation;
- eligible/excluded result explanations;
- current commercial offer display;
- accept/reject decisions for eligible persisted options;
- Portuguese/English UI;
- Light/Dark/System appearance;
- responsive desktop/tablet/mobile layout.

Authentication and production user-context discovery are not part of this increment.

## Dependency locking

This bootstrap pins all direct dependency versions but does not yet commit an npm lockfile. Local and CI validation therefore use `npm install --no-package-lock`. A committed lockfile is required before production deployment and should be added in a focused dependency-management hardening increment once the initial web toolchain is validated on the development machines and CI.
