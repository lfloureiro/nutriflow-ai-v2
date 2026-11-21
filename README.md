> **Estado atual — 19 novembro 2026:** consultar [passagem e próximos passos](docs/handoff-2026-11-19.md) e o [quadro UX](docs/vision/ux-revamp-task-board.md). Os estados de branches, contagens e “próxima tarefa” abaixo são históricos. Esta entrega consolida o revamp, o fluxo de trocas e o lote de 20; NLP/ML treinado e restantes fases continuam na sequência canónica.

# NutriFlow AI v2

NutriFlow AI v2 is a standalone, person-centric adaptive nutrition platform for individuals and families.

## Product direction

The core model is based on:

Person -> Family -> Health -> Schedule -> Meals -> Nutrition State -> Feedback

The system is designed to support:

- Individual nutrition profiles
- Family and shared meals
- Individual portions
- Dietary preferences and restrictions
- Medical and nutritionist-defined constraints
- Personal schedules
- Activity and health data
- Adaptive nutrition planning
- Recipes, pantry and shopping
- Restaurant and delivery meals
- Machine-learning-assisted meal selection

## Platform principles

NutriFlow AI v2 is designed from the beginning for:

- Multilingual support
- Light, dark and system themes
- Desktop and mobile layouts
- Responsive UI
- Web and native/mobile integration
- Apple Health / HealthKit
- Android Health Connect
- Future wearable and health-provider integrations

## Repository structure

apps/
  api/
  web/
  mobile/

packages/
  domain/
  nutrition/
  health/
  ui/
  i18n/
  shared/

database/
  migrations/
  seeds/

docs/
  vision/
  architecture/
  domain/
  ux/
  decisions/

tests/
tools/

## Current implementation status

The current backend foundation includes:

- Family and Person;
- PersonProfile;
- historical anthropometric measurements;
- NutritionGoal history;
- NutritionConstraint rules and provenance;
- FoodPreference records;
- FoodAdverseReaction records for allergies and intolerances;
- ScheduleEntry records for recurring and one-off availability context;
- versioned NutritionTarget snapshots with extensible nutrient components;
- person-scoped HealthConnection records for health-provider integrations;
- normalized HealthMeasurement records with provenance and cross-path deduplication identity;
- versioned DailyHealthState and DailyNutritionState snapshots with extensible nutrient progress components;
- family-scoped MealEvent records with MealParticipant associations;
- person-specific Serving records with planned, served and consumed quantities and nutrition components;
- FoodItem catalogue records with versioned FoodCompositionSnapshot nutrition data;
- Recipe and RecipeIngredient records with versioned RecipeCompositionSnapshot nutrition data;
- optional Serving links to FoodItem or Recipe while preserving historical serving snapshots;
- explicit Serving nutrition calculation from versioned catalogue composition with conservative unit conversion and persisted calculation provenance;
- deterministic meal recommendation ranking with hard-rule-first safety, nutrition fit, preferences and explainable scoring;
- fail-closed handling when an active mandatory nutrient maximum cannot be evaluated because candidate nutrient data is missing;
- persisted recommendation runs/options and append-only accepted/rejected/modified feedback events for future learning;
- materialization of accepted/modified recommendations into normal planned MealEvent, MealParticipant and Serving records using the exact recommendation composition snapshot;
- deterministic DailyNutritionState recalculation from authoritative Serving history using explicit local-day and target semantics;
- deterministic recommendation practical-context filtering from ScheduleEntry, location, preparation-window and kitchen availability inputs;
- fairness-first shared-family meal recommendation with person-specific portions and per-Person hard-rule evaluation;
- materialization of accepted shared-family recommendations into one MealEvent with person-specific Servings;
- Family-scoped MealEvent idempotency and immutable planned-meal replacement history for safe retries and later edits;
- persisted Family-scoped practical availability for home, pantry, restaurant, delivery and store meal sources;
- quantity-aware Family pantry stock with expiry, Recipe ingredient sufficiency and exact shopping requirements for missing quantities;
- restaurant/delivery/store opening windows plus provider-observed commercial offers with price, currency, delivery-fee, minimum-order and validity metadata;
- persisted person-scoped recommendation APIs using explicit DailyNutritionState and versioned composition evidence;
- recommendation decision API for accepted/rejected/modified persisted options, with accepted/modified decisions materialized through the standard MealEvent/MealParticipant/Serving model;
- practical recommendation orchestration combining Person schedule, home/pantry availability, pantry stock and commercial opening/offer evidence with any-source semantics;
- person-scoped planning bootstrap discovery of the latest local-day DailyNutritionState and current Family/global Food/Recipe composition evidence for the web UI;
- explicit, idempotent development demo data for exercising the real web/bootstrap/recommendation flow on a fresh local database;
- PostgreSQL persistence with Alembic migrations;
- pytest coverage with warnings treated as errors;
- Ruff static validation.

The initial web application includes:

- React + TypeScript + Vite under `apps/web`;
- responsive desktop/tablet/mobile layout;
- Portuguese and English UI strings through an i18n boundary;
- Light, Dark and System appearance modes;
- typed API client isolated from presentation code;
- Family -> Person selection followed by automatic server-authoritative planning bootstrap discovery;
- automatic DailyNutritionState selection for the chosen local meal instant;
- selectable FoodItem/Recipe names backed by current persisted composition snapshots, with technical composition UUIDs kept internal to the client;
- practical recommendation generation through the real orchestration API;
- eligible/excluded explanations, compact nutrition details and active commercial offer display;
- accept/reject actions over persisted recommendation options;
- Vitest unit tests plus strict TypeScript and production-build validation;
- a separate Web CI workflow.

The web still uses a development Family UUID entrypoint because authentication and household authorization context are not implemented yet. The meal-planning flow no longer requires users to type DailyNutritionState or composition snapshot UUIDs.

### Deploy local — único comando Windows

A partir de agora, o procedimento recomendado para o checkout de desenvolvimento
no Windows é executar **um único script**, a partir de qualquer diretório:

```powershell
D:\Python\nutriflow-ai-v2\deploy.ps1
```

Em alternativa, estando na pasta do projeto: ` .\deploy.ps1 `.

O `deploy.ps1` valida a branch e o estado limpo do Git, executa
`git fetch` e `git pull --ff-only`, assegura que o serviço PostgreSQL
definido em `compose.yml` está disponível, aplica Alembic e atualizações
aditivas do catálogo através de `python -m app.local_db_update`, atualiza
dependências quando os respetivos manifests mudam e reinicia apenas a API
ou o Vite afetados. Verifica `/openapi.json` e a página Vite após o arranque.

A gestão de processos usa PID, data de criação e porta, guardados em
`.nutriflow-local/deployment.json`, ignorado pelo Git, com logs na mesma
pasta. Não mata outros serviços por ocupar as portas 8000/5173. **Na
primeira execução**, se já houver servidores iniciados manualmente nessas
portas, termina-os uma única vez da forma habitual e volta a executar
`deploy.ps1`. A partir daí são lançados e geridos pelo script. Caso
esses serviços sejam controlados por um supervisor externo, deve utilizar-se
um deployment próprio desse supervisor.

Requer Python com as dependências do projeto, Docker Desktop/Compose,
Node.js e npm instalados. Não reinstala a BD, não faz `docker compose down`,
não executa `development_seed` completo e não apaga os dados familiares.
Falhas de rede, migração ou health check interrompem o deployment de
forma visível. O script **não é um deployment de produção**: destina-se
ao ambiente local com `APP_ENV=development`.

A opção `-ForceRestart` reinicia ambos os serviços quando necessário.
`-PythonPath` permite selecionar explicitamente o interpretador correto
numa instalação que use conda fora das pastas locais habituais.

O `deploy.ps1` deve passar a ser o único comando habitual para receber
versões novas. As instruções manuais seguintes ficam reservadas para
diagnóstico, recuperação e configuração inicial.

### Automatic local database updates after `git pull`

From NutriFlow v2.1.23 onward, restarting the API in `APP_ENV=development`
runs an incremental database update **before serving HTTP requests**:

1. Acquire a PostgreSQL advisory lock to prevent concurrent updates.
2. Apply pending **Alembic schema migrations** (`upgrade head`).
3. Apply idempotent, additive reference-catalogue updates (currently the
   milk-replacement ingredients and family transformation profiles).
4. Continue normal API startup. Startup fails visibly if the update fails,
   rather than serving an incompatible schema.

The update **does not reset/reseed the household**, delete meals, regenerate
recipe IDs, or alter existing user-selected transformation preferences.
It only registers reference data when the existing breakfast milk ingredient
is present. It does **not** make new families or import the entire legacy dataset.

**Normal workflow:** `git pull` the development branch, then restart the
existing API process (or allow the development reloader to restart it).
The updater is not triggered by GitHub itself: Git commits cannot directly
change a local PostgreSQL database. The web page refresh alone is insufficient
if the API has not restarted.

To run the same update explicitly without starting the server:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\api
python -m app.local_db_update
```

Set `NUTRIFLOW_AUTO_UPDATE_LOCAL_DB=false` to opt out. Automatic updates
never run for `APP_ENV=test` or `APP_ENV=production`: those environments
must use an explicit deployment migration workflow and verified catalogue
imports. Generic plant-milk nutrition in this development patch is
**provisional**, not independently verified product-label data or medical
clearance; substitutions still require each person's safety evaluation.

For any future data change, add an **idempotent, versioned catalogue patch**
to this updater and test repeated execution. Schema changes belong in Alembic.
Never run `python -m app.development_seed` as a routine update of an existing
family database because that command also imports complete sample datasets.

### Fresh local database

A new local database is intentionally empty. To create a synthetic development Family, Person, current DailyNutritionState and six meal candidates:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\api
python -m app.demo_seed
```

The command is explicit and idempotent; startup never auto-seeds. It prints the Family ID required by the current web development entrypoint. See `docs/domain/development-demo-dataset.md` and ADR-033.

Detailed domain status is maintained in `docs/domain/implementation-status.md`. Web flow decisions are documented under `docs/ux/` and `docs/decisions/`.

For a later development session, start with `docs/development-continuity.md`. It records the current checkpoint, exact resumption procedure, migration/test baseline and next safe development step.

## Development workflow

Changes are developed on focused branches rather than directly on `main`.

Before a branch is integrated it must:

- update relevant documentation and the continuity checkpoint;
- include or update tests;
- validate migrations locally when the database changes;
- pass the relevant local validation gates with zero warnings;
- open a PR only after local validation is green;
- pass CI on the exact PR head SHA;
- be squash-merged only after the tested head is confirmed unchanged.

The authoritative workflow decision is documented in `docs/decisions/ADR-007-development-workflow-and-ci.md`.

GitHub Actions runs API migration/Ruff/pytest validation and a separate web test/type-check/production-build gate.
