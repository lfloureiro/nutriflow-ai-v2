# Development demo dataset

## Purpose

A new local NutriFlow database is intentionally empty. The development demo dataset provides enough persisted evidence to exercise the integrated web planning flow without hand-creating Family, Person, DailyNutritionState or catalogue rows.

This is synthetic development data only. It is not production seed data and its nutrition values are not medical advice.

## Command

With PostgreSQL running and the API virtual environment active:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\api
python -m app.demo_seed
```

The command commits the demo rows and prints the fixed Family ID, Person ID, current planning date and candidate count.

Current demo Family ID:

```text
11111111-1111-4111-8111-111111111111
```

The current web application still asks for Family ID because authentication/authorization has not yet replaced that development entrypoint.

## Persisted data

The seed owns one dedicated Family and Person:

- Family: `NutriFlow Demo`;
- Person: `Pessoa Demo`;
- timezone: `Europe/Lisbon`;
- locale: `pt-PT`.

For the current Europe/Lisbon date it creates a DailyNutritionState with synthetic energy/protein/fiber/sodium progress. It also creates six Family-scoped `FoodItem` dishes with versioned `FoodCompositionSnapshot` nutrition evidence:

- Massa à bolonhesa;
- Frango com arroz e legumes;
- Salmão com batata e salada;
- Vaca com molho de ostras e arroz;
- Salada de grão, atum e ovo;
- Pizza pepperoni.

Every item contains energy plus protein, fiber and sodium nutrition data so the existing deterministic recommendation engine can evaluate the demo without missing-nutrient shortcuts.

The Person has:

- a synthetic `like` preference for the demo massa à bolonhesa, used only to exercise ranking explanations;
- a synthetic mandatory sodium maximum of 2300 mg, used only to exercise hard-rule exclusion.

Given the seeded daily sodium state, the pizza candidate is expected to be excluded by `mandatory_nutrient_max:sodium` while normal eligible candidates remain available.

## Idempotency and isolation

Running the command repeatedly is safe for the demo identities:

- the Family and Person are reused;
- the same catalogue items and composition version are reused;
- the same current-date DailyNutritionState calculation version is reused;
- unrelated Families and rows are not deleted or rewritten;
- reserved `demo:` catalogue-key ownership conflicts fail explicitly.

A later calendar date creates a new current-date demo DailyNutritionState rather than rewriting historical dates.

## Web smoke test

After seeding, run the API and web development servers. Open `http://127.0.0.1:5173`, enter the printed Family ID, choose `Pessoa Demo`, and use the normal planning form.

The browser obtains DailyNutritionState and composition IDs only through the server planning-bootstrap API. The seed does not bypass bootstrap, recommendation safety, persisted recommendation evidence or decision materialization.

## Validation

Automated tests verify:

- repeated seed execution is idempotent and leaves unrelated Family data untouched;
- the planning-bootstrap API sees the seeded current DailyNutritionState and all named demo candidates;
- the normal recommendation engine produces eligible candidates and the expected mandatory sodium exclusion.

Decision: ADR-033.
