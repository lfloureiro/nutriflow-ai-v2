# ADR-030: React + TypeScript + Vite is the initial web foundation

## Status

Accepted for the first NutriFlow AI v2 web vertical slice.

## Context

The backend now exposes a complete person-scoped recommendation path that can:

- load persisted Person safety/preferences/constraints;
- combine schedule, home, pantry and commercial availability;
- return explainable eligible/excluded recommendation options;
- persist recommendation evidence; and
- accept or reject an eligible persisted option through the standard meal materialization flow.

`apps/web` previously contained no application code. The target architecture already requires React + TypeScript, responsive UI, internationalisation, accessible components and Light/Dark/System appearance support.

The first web increment must validate those platform choices while exercising the real API instead of creating a disconnected mock product.

## Decision

The initial web application uses:

- React 19;
- TypeScript with strict type checking;
- Vite for development and production builds;
- Vitest for lightweight unit tests;
- native browser APIs and CSS design tokens rather than a component framework in the bootstrap increment.

The web application lives in `apps/web` and remains independent from backend business logic.

### Transport boundary

All API interaction is isolated in `src/api/`.

Presentation components do not reproduce recommendation, safety, nutrition, pantry or commercial decision logic. The server remains authoritative for eligibility, ranking, explanations and materialization.

During local development Vite proxies `/api` to FastAPI on `127.0.0.1:8000`. `VITE_API_BASE_URL` can point the application at another origin when needed.

### First vertical slice

The first UI is intentionally an integration/development slice rather than final onboarding.

It supports:

1. entering a Family ID;
2. loading and selecting a Person from the existing Family/Person API;
3. providing the explicit persisted DailyNutritionState ID required by the recommendation contract;
4. providing one or more explicit Food/Recipe composition snapshot IDs and quantities;
5. selecting practical context (scheduled time, location, available minutes, kitchen and source kinds);
6. calling the persisted practical recommendation API;
7. displaying eligible/excluded options, nutrition, explanations, exclusions and active commercial offers;
8. accepting or rejecting an eligible option through the persisted decision API.

The UI does not infer DailyNutritionState or composition versions because the backend does not yet expose a safe discovery/selection policy for those values.

### Internationalisation

User-facing application strings are accessed through translation keys. The bootstrap supports `pt-PT` and English.

Locale selection is a presentation preference. It does not mutate Person locale or server-side domain state in this increment.

### Appearance and responsive design

Colour, spacing, typography, semantic states and radii use CSS custom-property design tokens.

The app supports Light, Dark and System appearance modes and responsive desktop/tablet/mobile layouts from the first slice.

### Dependency installation

Direct dependency versions are pinned in `apps/web/package.json`.

This bootstrap does not yet commit an npm lockfile. Local validation and Web CI use `npm install --no-package-lock --ignore-scripts` so the working tree remains unchanged during the current gate.

A committed lockfile is mandatory before production deployment and is a recorded follow-up hardening task. This temporary choice must not be interpreted as a general policy against lockfiles.

## Consequences

Positive:

- the first UI exercises real persisted backend contracts;
- React/TypeScript matches the documented target architecture;
- business/safety logic stays server-side;
- the UI is responsive and multilingual from the beginning;
- no large component framework constrains the design system before product patterns stabilise;
- a separate Web CI gate now validates tests and production builds.

Trade-offs:

- the initial form exposes internal persisted IDs and is not yet normal-user onboarding;
- catalogue and DailyNutritionState discovery APIs are now clearly the next usability gap;
- the initial dependency install is not transitively reproducible until the lockfile hardening task is completed;
- authentication/user context is still absent and must be added before real multi-user deployment.

## Follow-up

After this slice is validated and merged:

1. add safe UI-facing discovery of current DailyNutritionState and eligible catalogue compositions so UUID entry disappears;
2. add authentication and Family/Person authorization context before production use;
3. add a committed npm lockfile and switch CI to `npm ci`;
4. grow reusable components into `packages/ui` only when multiple real screens need them;
5. add browser/E2E coverage once stable user flows exist.
