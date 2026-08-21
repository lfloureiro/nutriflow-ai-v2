# ADR-003 — Internationalisation, themes and responsive layouts are foundational

## Status
Accepted

## Decision

NutriFlow AI v2 must support internationalisation, Light/Dark/System appearance modes and desktop/tablet/mobile layouts from the beginning.

These are architectural requirements, not later UI enhancements.

## Requirements

- no hard-coded user-facing strings in components;
- locale-specific translation resources;
- locale-aware dates, numbers and units;
- per-user language/locale preference;
- design tokens instead of hard-coded colours;
- Light, Dark and System themes;
- responsive components and defined breakpoints;
- accessibility considered at component level.

## Rationale

Adding these capabilities after a large UI has been built creates extensive rework and inconsistent behaviour. The product is intended to work for multiple people within a family and across web/mobile contexts, so these concerns are cross-cutting from the start.

## Consequences

Shared UI and i18n packages are first-class repository components. New screens are not considered complete if they only work in one theme, language strategy or viewport class.
