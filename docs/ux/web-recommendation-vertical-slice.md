# First web recommendation vertical slice

## Purpose

This is the first real NutriFlow AI v2 web UI. Its goal is to validate the React/TypeScript platform and exercise the current persisted recommendation and decision APIs end to end.

It is not final onboarding. Internal persisted IDs are deliberately visible because the backend does not yet expose safe discovery/selection APIs for DailyNutritionState and catalogue composition snapshots.

## User flow

```text
Family ID
   ↓
Load people
   ↓
Choose Person
   ↓
Enter explicit DailyNutritionState
   ↓
Enter one or more Food/Recipe composition candidates
   ↓
Set meal time + practical context
   ↓
Request practical recommendation
   ↓
Review eligible/excluded options and explanations
   ↓
Accept or reject an eligible option
   ↓
Accepted option is materialized by the backend into the normal meal plan
```

## Screen structure

### Header

Contains:

- NutriFlow identity;
- language selector (`pt-PT`, English);
- appearance selector (System, Light, Dark).

### Step 1 — Person

The user enters a Family UUID. The UI calls:

```text
GET /api/families/{family_id}/persons
```

and displays the returned Persons in a selector.

Authentication is not implemented yet, so Family ID entry is a temporary developer/integration boundary rather than the final household selection experience.

### Step 2 — Meal context

The form captures the data already required by the practical recommendation API:

- DailyNutritionState UUID;
- planning date;
- timezone-aware scheduled instant derived from the browser local date/time input;
- meal type;
- optional location;
- optional available minutes;
- kitchen state: yes/no/unknown;
- source kinds: home, pantry, restaurant, delivery, store;
- one or more Food/Recipe composition snapshot IDs with quantity/unit.

At least one practical source remains selected.

The request is sent to:

```text
POST /api/persons/{person_id}/meal-recommendations/practical
```

All eligibility, safety, nutrition and practical evaluation remains server-side.

### Step 3 — Recommendation results

Every persisted recommendation option is shown, including excluded options.

Cards display, when available:

- candidate name and requested quantity;
- eligible/excluded state and rank;
- energy and a compact nutrient summary;
- server explanation strings;
- explicit exclusion reason codes;
- current active commercial offers for that candidate;
- known provider total in the offer currency.

No client-side re-ranking or safety filtering is performed.

### Decision actions

Eligible cards expose Accept and Reject actions.

Accept sends the current schedule/location plus the selected Person timezone to:

```text
POST /api/recommendation-options/{option_id}/decision
```

with `action=accepted`.

Reject sends only rejection feedback plus a web-entrypoint metadata marker.

The UI displays the persisted result and, for accepted options, whether a meal event was created.

## Responsive behaviour

Desktop:

- Person setup remains in a smaller left column;
- planning form occupies the main column;
- recommendation cards use a multi-column grid.

Tablet:

- setup and planning stack vertically;
- result cards reduce to two columns.

Mobile:

- all major workflow sections are single-column;
- candidate rows reflow vertically;
- commercial offer and decision actions stack;
- core controls remain touch-sized.

## Accessibility baseline

The slice uses semantic forms, labels, fieldsets, status/error roles and keyboard-focus styling.

Accessibility is a component-level requirement. Future shared components must preserve semantic labels and visible focus rather than relying on visual layout alone.

## Internationalisation

All authored user-facing UI strings are resolved from translation keys. Portuguese (`pt-PT`) and English are included in the first slice.

Server explanation and exclusion strings are currently displayed as returned because the backend does not yet expose localized explanation codes/messages separately. A later API/UI refinement should map stable server reason codes to localized presentation strings while preserving raw audit evidence.

## Appearance

The UI supports System, Light and Dark modes. The selected presentation preference is stored locally in the browser and does not mutate Person domain state.

## Known limitations / next usability work

The following are intentionally not solved in this slice:

- authentication and automatic household context;
- Family discovery;
- automatic current DailyNutritionState discovery/selection;
- Food/Recipe catalogue browse/search and composition selection;
- accepted-source/provider selection persistence;
- editing/modifying an option through the web UI;
- meal-plan/history view after acceptance;
- localized rendering of server explanation/reason codes;
- browser-level E2E tests;
- PWA/native integration.

The highest-value next web/API increment is to remove UUID entry by exposing safe planning bootstrap/discovery data for the selected Person.
