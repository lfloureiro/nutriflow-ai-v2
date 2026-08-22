# Person overview

## Purpose

The Person overview is the first drill-down from the Family Home. It answers one question:

> Como está esta pessoa hoje?

It is intentionally compact. It should not become a second dense dashboard and it should not duplicate the Family Home.

## Entry points

A Person can be opened from:

- a Person card on `Início`;
- the `Pessoas` primary destination.

Opening `Pessoas` directly shows the Family member list. Selecting a member opens that Person overview. The back action returns to the member list.

## Secondary navigation

Once a Person is open, the secondary destinations are:

```text
Visão geral
Nutrição
Atividade
Saúde
Histórico
Perfil
```

The first increment implements `Visão geral`. The other destinations are visible, lightweight placeholders so the information architecture is explicit without inventing data or pretending detailed read models already exist.

## Overview content

`Visão geral` presents only current-day evidence already available from the Family dashboard read model:

- energy consumed plus remaining range when available;
- steps plus active energy when available;
- latest weight plus persisted 7-day trend when available;
- sleep duration plus resting heart rate when available;
- current-day meals in which the Person participates.

Missing values render as `Sem dados` / `No data`. The browser never substitutes zero and does not fall back to an older day.

No chart is included in this first slice because the current Family dashboard response contains compact current-day summaries and weight-trend deltas, not a historical time series. A future Person read model can add the single primary trend chart allowed by ADR-034.

## Person-specific meals

The overview filters the Family dashboard meal agenda by `participant_person_ids` and displays only meals containing the selected Person.

Known domain enum values are localized for presentation (`lunch` -> `Almoço`, `planned` -> `Planeada`, `completed` -> `Concluída`). Unknown values are shown unchanged rather than guessed.

This is presentation filtering only. It does not replace the Family MealEvent/MealParticipant domain model or calculate portions in the browser. Person-specific portion drill-down remains a later meal-detail increment.

Distinct persisted MealEvents remain distinct rows even when they share a time or title. Development/demo cleanup must be explicit rather than hidden by client-side deduplication.

## Safety and authority boundary

The Person overview:

- presents persisted DailyHealthState/DailyNutritionState evidence;
- does not infer medical status or calculate a health score;
- does not reproduce nutrition safety/ranking logic;
- does not select historical evidence versions itself;
- preserves missing evidence as missing;
- does not calculate targets, recommendations or meal portions.

## Responsive behavior

Desktop/tablet:

- secondary navigation is a compact horizontal row;
- current-day indicators use a small grid;
- Person meals use simple chronological rows.

Mobile:

- secondary navigation remains horizontally scrollable rather than becoming a large menu;
- indicators become a single column;
- meal rows remain compact;
- the primary app navigation remains the existing bottom navigation.

## Follow-up screens

Detailed sections require focused future increments and, where necessary, dedicated server read models:

- `Nutrição`: targets, intake/planned detail and nutrient progress;
- `Atividade`: movement, energy and activity history;
- `Saúde`: wellness evidence and connected-source observations;
- `Histórico`: chronological trends and events;
- `Perfil`: goals, constraints, preferences and integrations.

Related decisions/documents:

- `docs/decisions/ADR-034-family-first-progressive-disclosure-web-navigation.md`;
- `docs/ux/frontend-information-architecture.md`;
- `docs/ux/family-home-shell.md`.
