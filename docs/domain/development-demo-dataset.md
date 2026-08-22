# Development demo dataset

## Purpose

A new local NutriFlow database is intentionally empty. The development demo dataset provides enough persisted evidence to exercise the integrated Family Home and meal-planning flow without hand-creating Family, Person, health, nutrition, meal-agenda or catalogue rows.

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

This lets the Home exercise chronological agenda rendering, participant names, shared meals, locations and mixed statuses.

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
- the same current-date agenda MealEvents and MealParticipants are reused;
- the original primary Person DailyNutritionState identity is preserved for compatibility with existing local demo databases;
- unrelated Families and rows are not deleted or rewritten;
- reserved `demo:` catalogue-key and demo meal idempotency-key ownership conflicts fail explicitly.

A later calendar date creates new deterministic current-date health/nutrition and agenda rows rather than rewriting historical dates.

## Web smoke test

After seeding, run the API and web development servers and open `http://127.0.0.1:5173`.

`Início` should show four member cards with intentionally different evidence/missing-data combinations and three meals in the current-day agenda. `Refeições` should still allow `Pessoa Demo` to exercise planning bootstrap, recommendation safety/ranking and accept/reject decisions.

The browser obtains authoritative DailyNutritionState/composition IDs through the server APIs. The seed does not bypass bootstrap, recommendation safety, persisted recommendation evidence or decision materialization.

## Validation

Automated tests verify:

- repeated seed execution is idempotent and leaves unrelated Family data untouched;
- the expected Family members, health states, agenda events and participants are created once;
- the Family dashboard API exposes the intended variation and missing evidence;
- the planning-bootstrap API still sees the primary current DailyNutritionState and all named demo candidates;
- the normal recommendation engine still produces eligible candidates and the expected mandatory sodium exclusion.

Decision: ADR-033.
