# ADR-034: Family-first progressive-disclosure web navigation

## Status

Accepted.

## Context

The first NutriFlow web slice proved the recommendation flow but is structurally a developer-oriented workflow screen. The product now needs an information architecture that can scale across family health/activity, individual nutrition, meals, pantry and settings without turning the application into a dense analytics cockpit.

The product is family-centric but Person-specific in its health, nutrition, safety and portion semantics. The frontend must expose both levels without duplicating or flattening those distinctions.

## Decision

NutriFlow web will use a family-first application structure with progressive disclosure.

Primary navigation:

- Início;
- Refeições;
- Pessoas;
- Casa;
- Mais.

`Início` is a lightweight family overview for the current day. It is not the meal planner and it is not a comprehensive health dashboard. It provides compact member cards, today's meal agenda and limited next-action context.

Person cards drill into a Person overview. Detailed health, activity, nutrition, history and profile content lives on separate screens rather than expanding the family Home indefinitely.

Meals remain a parallel family workflow. Shared meals are shown once at family level and drill down to Person-specific portions/outcomes.

Desktop uses compact side navigation. Mobile uses compact bottom navigation for the same primary destinations.

The browser remains a presentation/orchestration layer. Family Home aggregation is supplied by a dedicated server read model rather than assembled through many client requests.

## UX constraints

- Prefer more focused screens over large multi-widget screens.
- One screen should answer one primary question.
- Home should normally contain zero or one small chart.
- Person overview should normally contain at most one primary chart.
- Dedicated analytical screens may contain additional charts.
- Missing evidence is explicitly unavailable/unknown, never zero.
- No aggregate health score is invented without a future explicit domain definition.
- Existing backend safety and nutrition rules are not reimplemented in the browser.

## API consequence

A compact Family Home read model is required. The first endpoint is:

```text
GET /api/families/{family_id}/dashboard?on_date=YYYY-MM-DD
```

The date parameter is optional. When omitted, the server resolves today in the persisted Family timezone.

The response exposes current-day member health/nutrition evidence and active current-day family meals. It does not derive medical interpretation or a synthetic family score.

## Consequences

Positive:

- information density remains controlled as capabilities grow;
- family and Person concepts remain visible and distinct;
- navigation maps naturally to desktop and mobile;
- future data sources can enrich dedicated screens without destabilizing Home;
- server-authoritative aggregation reduces client complexity and request fan-out.

Trade-offs:

- more screens/routes must be designed and maintained;
- users may perform an extra navigation step to reach deep detail;
- read-model endpoints are needed for key screens even when underlying domain data already exists.

These trade-offs are accepted because clarity and long-term product scalability are more important than minimizing click count or maximizing information per screen.

## Related documents

- `docs/ux/frontend-information-architecture.md`
- `docs/domain/family-dashboard-read-model.md`
- `docs/decisions/ADR-007-development-workflow-and-ci.md`
