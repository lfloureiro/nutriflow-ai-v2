# ADR-007: Development workflow and continuous integration

## Status

Accepted

## Context

NutriFlow AI v2 is developed incrementally across domain, persistence, API, web and mobile layers. The repository itself must contain enough information to resume work safely after a long interruption or in a new development session without depending on chat history.

Direct changes to `main` make it harder to validate a coherent change set before it becomes part of the stable baseline. Database migrations require local verification against PostgreSQL before they are accepted. Documentation, automated tests and static checks must evolve together with implementation so architecture decisions, current behaviour and the next safe development step remain traceable.

The project also treats warnings as failures. A change is not complete merely because its functional tests pass; migration metadata, Ruff and the complete pytest suite must all be clean.

## Decision

`main` is the tested integration baseline. Non-trivial changes are never developed directly on `main`.

Every change uses this sequence:

1. Resolve the exact current `main` commit and update the local checkout.
2. Create one focused feature branch from that exact `main` commit.
3. Implement the complete code change on the feature branch.
4. Add or update the database migration when persistence changes.
5. Add or update tests for all changed behaviour, including safety and failure paths where relevant.
6. Update all relevant domain documentation, ADRs, implementation status and continuation/handover notes on the same branch.
7. Run local validation against PostgreSQL.
8. Require Alembic metadata validation, Ruff and the complete pytest suite to pass with zero warnings.
9. Only after the user/developer confirms all local gates are green, open a pull request targeting `main`.
10. Verify GitHub Actions on the exact pull-request head commit, not merely on an earlier commit from the branch.
11. Require the pull request to remain mergeable and its head SHA to remain unchanged after CI succeeds.
12. Squash-merge the pull request using the exact tested head SHA.
13. Verify that the pull request is closed and merged and record/confirm the resulting exact `main` SHA.
14. Do not start the next feature branch until the previous pull request is merged and the new `main` SHA is known.

Direct commits to `main`, merging an untested branch, opening a pull request before local validation, or continuing from a stale `main` are outside the accepted workflow.

## Local validation gates

For a branch without schema changes, the minimum local gates are:

```powershell
python -m alembic check

cd apps\api
python -m ruff check .
python -m pytest -q
```

For a branch with a new migration, the minimum local gates are:

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic check

cd apps\api
python -m ruff check .
python -m pytest -q
```

Expected properties:

- `alembic upgrade head` succeeds against the local PostgreSQL database;
- `alembic current` reports the intended head revision;
- `alembic check` reports `No new upgrade operations detected.`;
- Ruff reports `All checks passed!`;
- pytest reports the complete suite passing;
- no warning is tolerated because pytest is configured with warnings as errors.

When a feature branch already exists locally, switch to it and pull rather than attempting to recreate it. When it does not exist locally, create the local tracking branch from `origin/<feature-branch>`.

## Pull request and merge gates

A pull request is created only after local validation is explicitly green.

Before merge:

- compare the feature branch with `main` and confirm it is based on the expected merge base;
- confirm it is not behind `main`;
- record the exact feature-branch head SHA;
- run CI for that exact SHA;
- inspect the API CI job and require database migrations, Alembic metadata validation, Ruff and the complete API test suite all to succeed;
- confirm the PR is mergeable;
- confirm the PR head still equals the SHA that CI tested.

The merge method is squash. The merge operation must be guarded by the expected head SHA so a branch that changes after CI cannot be merged accidentally.

After merge, verify the PR reports `merged=true` and verify the exact resulting `main` SHA before any new branch is created.

## Continuous integration

GitHub Actions provides an independent verification layer.

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

CI complements local validation. It does not replace local validation, and a green CI run for a different commit does not authorize merging the current branch head.

## Documentation and continuity policy

Documentation is part of the definition of done, not cleanup after implementation.

Every material domain or architecture change must update, as applicable:

- the relevant `docs/domain/` document;
- an ADR under `docs/decisions/` when a durable design decision is introduced;
- `docs/domain/implementation-status.md`;
- `README.md` when the repository-level capability summary changes;
- `docs/development-continuity.md` whenever the current checkpoint, next safe step, migration head, test baseline or workflow assumptions change materially.

The continuation document is the entry point for resuming development in a later session. It must point back to authoritative domain documents and ADRs rather than duplicating all domain semantics.

Code, migration, tests and documentation are expected to land in the same feature branch and the same pull request.

## Definition of done

A feature increment is complete only when all of the following are true:

- implementation is complete for the declared scope;
- migrations are present and reversible when schema changes are required;
- tests cover the new behaviour and important failure paths;
- documentation and ADRs are current;
- continuation/handover state is current;
- local Alembic validation is clean;
- Ruff is clean;
- the complete local pytest suite passes with zero warnings;
- the pull request CI passes on the exact head SHA;
- the feature is squash-merged;
- the resulting `main` SHA is verified.

## Consequences

Benefits:

- `main` remains a validated baseline;
- regressions, migration drift, lint violations and warnings are caught before integration;
- migrations are tested both locally and from a clean CI database;
- documentation remains aligned with implementation;
- every domain increment has a reviewable and reversible history;
- a future development session can resume from repository documentation instead of relying on conversational memory.

Costs:

- changes require a focused branch, local validation, PR and CI cycle;
- database-related work requires both local PostgreSQL and CI verification;
- documentation and handover maintenance are mandatory parts of each increment;
- the next increment cannot begin until the current one is merged and the new `main` commit is known.
