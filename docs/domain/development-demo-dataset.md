# Development demo dataset

## Purpose

A new local NutriFlow database is intentionally empty. The development demo dataset provides enough persisted evidence to exercise the integrated Family Home, Family meal map/detail and meal-planning flow without hand-creating Family, Person, health, nutrition, meal-agenda, Serving or catalogue rows.

This is synthetic development data only. It is not production seed data, real health history or medical advice.

## Command

With PostgreSQL running and the API virtual environment active:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\api
python -m app.demo_seed
```

The command commits the demo rows and prints the fixed Family ID, primary Person ID, current planning date, member count, meal count and candidate count.

Current demo Family ID:

```text
11111111-1111-4111-8111-111111111111
```

The Vite development shell may select this Family automatically when no previous development Family context is stored. The UI never runs the seed itself.

## Family Home evidence

The seed owns one dedicated Family with four synthetic members:

- `Pessoa Demo` — the primary planning/recommendation Person;
- `Marta Demo`;
- `Rui Demo`;
- `Inês Demo`.

All use `Europe/Lisbon` and `pt-PT`.

For the current Europe/Lisbon date, the seed creates deliberately varied dashboard evidence:

- three members have DailyNutritionState summaries with different consumed/planned energy and adherence values;
- `Inês Demo` deliberately has no DailyNutritionState so the Home exercises the explicit missing-data state;
- all four have DailyHealthState rows with varied steps, weight trends, sleep and activity evidence;
- `Rui Demo` deliberately has no current weight evidence;
- `Inês Demo` deliberately has no sleep/heart/recovery evidence.

The values are synthetic and exist only to make the visual states of the Family Home easy to inspect.

The current-day agenda contains three deterministic Family MealEvents:

- 08:00 — `Pequeno-almoço`, completed, four participants;
- 13:00 — `Almoço`, planned, two participants;
- 20:00 — `Jantar em família`, planned, four participants.

This lets the Home and `Refeições > Hoje` exercise chronological agenda rendering, participant names, shared meals, locations and mixed statuses.

## Person-specific demo portions

Every one of the ten current-day demo MealParticipants has one deterministic synthetic Serving so the shared-meal detail screen is useful immediately after seeding.

The portions deliberately differ by Person. Examples:

- lunch `Massa à bolonhesa`: `Pessoa Demo` 400 g / 650 kcal, `Rui Demo` 500 g / 812.5 kcal;
- dinner `Salmão com batata e salada`: 400 g for `Pessoa Demo`, 320 g for Marta, 500 g for Rui and 300 g for Inês.

The completed breakfast uses consumed Serving evidence; lunch and dinner use planned Serving evidence. This allows the frontend to exercise both realized and future portion states.

These Serving values are explicit synthetic fixtures identified by demo source/version/reference metadata. They exist to exercise presentation and lifecycle state, not to substitute for the production Serving nutrition-calculation path or establish new nutrition semantics.

Repeated seeding reuses deterministic Serving IDs, so it does not duplicate portions.

## Planning and recommendation evidence

The primary `Pessoa Demo` keeps the original recommendation fixture behavior. Its current DailyNutritionState contains synthetic energy/protein/fiber/sodium progress.

The Family also owns six `FoodItem` dishes with versioned `FoodCompositionSnapshot` evidence:

- Massa à bolonhesa;
- Frango com arroz e legumes;
- Salmão com batata e salada;
- Vaca com molho de ostras e arroz;
- Salada de grão, atum e ovo;
- Pizza pepperoni.

Every item contains energy plus protein, fiber and sodium so the deterministic recommendation engine can evaluate the demo without missing-nutrient shortcuts.

`Pessoa Demo` has:

- a synthetic `like` preference for `Massa à bolonhesa`, used to exercise ranking explanations;
- a synthetic mandatory sodium maximum of 2300 mg, used to exercise hard-rule exclusion.

Given the seeded sodium state, `Pizza pepperoni` is expected to be excluded by `mandatory_nutrient_max:sodium` while normal eligible candidates remain available.

## Idempotency and isolation

Running the command repeatedly is safe for the reserved demo identities:

- the Family and four Persons are reused;
- the same catalogue items and composition version are reused;
- the same current-date health/nutrition calculation versions are reused;
- the same current-date agenda MealEvents, MealParticipants and Person-specific Servings are reused;
- the original primary Person DailyNutritionState identity is preserved for compatibility with existing local demo databases;
- unrelated Families and rows are not deleted or rewritten;
- reserved `demo:` catalogue-key and demo meal idempotency-key ownership conflicts fail explicitly.

A later calendar date creates new deterministic current-date health/nutrition, agenda and Serving rows rather than rewriting historical dates.

## Web smoke test

After seeding, run the API and web development servers and open `http://127.0.0.1:5173`.

`Início` should show four member cards with intentionally different evidence/missing-data combinations and three meals in the current-day agenda.

Under `Refeições > Hoje`, open any of the three meals. The `Refeição` drill-down should show the persisted participants and their individual portion evidence. The dinner is especially useful because all four members share the same dish with visibly different quantities.

`Refeições > Recomendar` should still allow `Pessoa Demo` to exercise planning bootstrap, recommendation safety/ranking and accept/reject decisions.

The browser obtains authoritative DailyNutritionState/composition IDs through the server APIs. The seed does not bypass bootstrap, recommendation safety, persisted recommendation evidence or decision materialization.

## Validation

Automated tests verify:

- repeated seed execution is idempotent and leaves unrelated Family data untouched;
- the expected Family members, health states, agenda events, participants and ten Servings are created once;
- the Family dashboard API exposes the intended variation and missing evidence;
- the Family meal-detail API is independently covered for Person-specific portions and cross-Family isolation;
- the planning-bootstrap API still sees the primary current DailyNutritionState and all named demo candidates;
- the normal recommendation engine still produces eligible candidates and the expected mandatory sodium exclusion.

Decision: ADR-033.
