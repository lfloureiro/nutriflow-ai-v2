# ADR-007: Development workflow and continuous integration

## Status

Accepted

## Context

NutriFlow AI v2 is developed incrementally across domain, persistence, API, web and mobile layers. The repository itself must contain enough information to resume work safely after a long interruption or in a new development session without depending on chat history.

Direct changes to `main` make it harder to validate a coherent change set before it becomes part of the stable baseline. Database migrations require local verification against PostgreSQL before they are accepted. Web/mobile/package changes require their own static-analysis, test and build gates. Documentation, automated tests and validation must evolve together with implementation so architecture decisions, current behaviour and the next safe development step remain traceable.

The project treats warnings as failures where the relevant toolchain supports that policy. A change is not complete merely because one application test suite passes; every affected application/package and the integrated repository gates relevant to the branch must be clean.

## Decision

`main` is the tested integration baseline. Non-trivial changes are never developed directly on `main`.

Every change uses this sequence:

1. Resolve the exact current `main` commit and update the local checkout.
2. Create one focused feature branch from that exact `main` commit.
3. Implement the complete code change on the feature branch.
4. Add or update the database migration when persistence changes.
5. Add or update tests for all changed behaviour, including safety and failure paths where relevant.
6. Update all relevant domain/UX/architecture documentation, ADRs, implementation status and continuation/handover notes on the same branch.
7. Run every local validation gate relevant to the affected applications/packages and integrated product boundary.
8. Require all relevant migration, static-analysis, type-check, test and production-build gates to pass with zero warnings/errors.
9. Only after the user/developer confirms all relevant local gates are green, open a pull request targeting `main`.
10. Verify every relevant GitHub Actions workflow on the exact pull-request head commit, not merely on an earlier commit from the branch.
11. Require the pull request to remain mergeable and its head SHA to remain unchanged after CI succeeds.
12. Squash-merge the pull request using the exact tested head SHA.
13. Verify that the pull request is closed and merged and record/confirm the resulting exact `main` SHA.
14. Do not start the next feature branch until the previous pull request is merged and the new `main` SHA is known.

Direct commits to `main`, merging an untested branch, opening a pull request before local validation, or continuing from a stale `main` are outside the accepted workflow.

## Local validation gates

Validation is cumulative: run the gates for every area the branch affects. Cross-cutting changes such as workflow/configuration/docs accompanying an application increment should preserve the existing integrated application baselines as well.

### API/backend branch without schema changes

```powershell
python -m alembic check

cd apps\api
python -m ruff check .
python -m pytest -q
```

### API/backend branch with a new migration

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic check

cd apps\api
python -m ruff check .
python -m pytest -q
```

Expected API properties:

- `alembic upgrade head` succeeds against the local PostgreSQL database when required;
- `alembic current` reports the intended head revision when required;
- `alembic check` reports `No new upgrade operations detected.`;
- Ruff reports `All checks passed!`;
- pytest reports the complete suite passing;
- no Python warning is tolerated because pytest is configured with warnings as errors.

### Web branch

For changes affecting `apps/web`, web contracts or Web CI:

```powershell
cd apps\web
npm install --no-package-lock --ignore-scripts
npm run test
npm run build
```

During the initial web bootstrap, `npm run build` includes strict TypeScript validation followed by the production Vite build. The temporary no-lockfile install policy is documented in ADR-030 and must be replaced by a committed lockfile plus `npm ci` before production deployment.

A web branch that integrates with existing API contracts should also run the API regression gates unless the branch is explicitly isolated and the repository workflow has been amended to prove otherwise. The first web vertical slice therefore requires both the current API baseline and the web gates to remain green.

### Future applications/packages

When mobile or shared packages acquire executable toolchains, their local test/lint/type/build commands become mandatory gates for branches that affect them. This ADR must be updated with the concrete commands rather than relying on undocumented conventions.

When a feature branch already exists locally, switch to it and pull rather than attempting to recreate it. When it does not exist locally, create the local tracking branch from `origin/<feature-branch>`.

## Pull request and merge gates

A pull request is created only after local validation is explicitly green for the exact complete branch head.

Before merge:

- compare the feature branch with `main` and confirm it is based on the expected merge base;
- confirm it is not behind `main`;
- record the exact feature-branch head SHA;
- run every relevant CI workflow for that exact SHA;
- inspect each relevant workflow/job and require all migration/static-analysis/type-check/test/build steps to succeed;
- confirm the PR is mergeable;
- confirm the PR head still equals the SHA that CI tested.

The merge method is squash. The merge operation must be guarded by the expected head SHA so a branch that changes after CI cannot be merged accidentally.

After merge, verify the PR reports `merged=true` and verify the exact resulting `main` SHA before any new branch is created.

## Continuous integration

GitHub Actions provides an independent verification layer. CI complements local validation; it does not replace it, and a green CI run for a different commit does not authorize merging the current branch head.

### API CI

The API CI workflow must:

- run on branch pushes and pull requests targeting `main`;
- use Python 3.13;
- start PostgreSQL for integration validation;
- install the API including development/test dependencies;
- apply all Alembic migrations from an empty database;
- run `alembic check` to detect model/schema drift;
- run Ruff across the API package and tests;
- run the full API pytest suite;
- fail on Python warnings because pytest is configured with `filterwarnings = ["error"]`.

### Web CI

Once `apps/web` contains executable application code, Web CI must independently validate it.

The initial Web CI workflow must:

- run on branch pushes and pull requests targeting `main`;
- use Node.js 22;
- install the pinned direct web dependencies according to the current dependency policy;
- run the complete Vitest suite;
- run strict TypeScript validation;
- create a production Vite build;
- fail the workflow if any of those steps fail.

When the committed npm lockfile is added, Web CI must switch from the bootstrap install command to `npm ci`.

For a PR that changes both API and web behavior/contracts, both relevant workflows must pass on the same exact PR head SHA before merge.

## Documentation and continuity policy

Documentation is part of the definition of done, not cleanup after implementation.

Every material domain, architecture or UX change must update, as applicable:

- the relevant `docs/domain/`, `docs/architecture/` or `docs/ux/` document;
- an ADR under `docs/decisions/` when a durable design decision is introduced;
- `docs/domain/implementation-status.md`;
- `README.md` when the repository-level capability summary changes;
- application/package README files when local setup/validation changes;
- `docs/development-continuity.md` whenever the current checkpoint, next safe step, migration head, test/build baseline or workflow assumptions change materially.

The continuation document is the entry point for resuming development in a later session. It must point back to authoritative domain/UX documents and ADRs rather than duplicating all semantics.

Code, migrations when needed, tests, CI and documentation are expected to land in the same feature branch and the same pull request.

## Definition of done

A feature increment is complete only when all of the following are true:

- implementation is complete for the declared scope;
- migrations are present and reversible when schema changes are required;
- tests cover the new behaviour and important failure paths;
- documentation and ADRs are current;
- continuation/handover state is current;
- all relevant local migration/static/type/test/build gates are clean;
- zero-warning/error policy is satisfied for the applicable toolchains;
- every relevant pull-request CI workflow passes on the exact head SHA;
- the feature is squash-merged using the expected tested head;
- the resulting `main` SHA is verified.

## Consequences

Benefits:

- `main` remains a validated baseline across backend and frontend applications;
- regressions, migration drift, lint/type violations, broken production builds and warnings are caught before integration;
- migrations are tested both locally and from a clean CI database;
- web changes are validated independently from the API rather than assuming a backend-only gate is sufficient;
- documentation remains aligned with implementation;
- every increment has a reviewable and reversible history;
- a future development session can resume from repository documentation instead of relying on conversational memory.

Costs:

- changes require a focused branch, local validation, PR and CI cycle;
- multi-application changes require more than one validation suite;
- database-related work requires both local PostgreSQL and CI verification;
- documentation and handover maintenance are mandatory parts of each increment;
- the next increment cannot begin until the current one is merged and the new `main` commit is known.
