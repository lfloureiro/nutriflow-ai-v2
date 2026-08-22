# ADR-033: Development demo data is explicit, idempotent and isolated

## Status

Accepted.

## Context

The first usable web planning flow is now integrated, but a fresh local PostgreSQL database contains no Family, Person, DailyNutritionState or catalogue evidence. That makes the UI impossible to exercise without hand-authoring internal UUIDs and persistence rows.

Development data must not weaken production domain boundaries, silently appear in real environments, or become an alternative source of nutrition truth.

## Decision

NutriFlow provides an explicit development-only seed command implemented in `app.demo_seed`.

The seed:

- is invoked manually; application startup never auto-seeds;
- uses a dedicated fixed Family and Person identity for the demo household;
- uses `demo:` catalogue keys and `source="demo"` provenance;
- creates only synthetic development data;
- creates the DailyNutritionState for the current Europe/Lisbon local date;
- is idempotent for the same date and catalogue version;
- updates only the dedicated demo identities it owns;
- does not delete or rewrite unrelated user/Families data;
- raises an explicit conflict if a reserved demo catalogue key belongs to another FoodItem;
- preserves the normal persisted-evidence boundaries used by planning bootstrap and recommendation APIs.

The demo intentionally contains a normal preference signal and a mandatory sodium maximum so local UI testing exercises both ranking explanation and hard-rule exclusion. These are synthetic examples, not medical recommendations.

The seed command is:

```powershell
cd apps\api
python -m app.demo_seed
```

It prints the Family ID required by the current pre-authentication web entrypoint.

## Consequences

A fresh developer database can be made usable in one explicit command while still exercising the same bootstrap/recommendation/decision paths as normal persisted data.

Demo rows may remain in a local database across sessions and a new demo DailyNutritionState may be created on later dates. This is acceptable development data. Production deployment must not invoke the seed.

Authentication/authorization remains responsible for removing Family UUID entry from the real product; the demo seed is not an authentication substitute.
