# ADR-007: Development workflow and continuous integration

## Status

Accepted

## Context

NutriFlow AI v2 is being developed incrementally across domain, persistence, API, web and mobile layers.

Direct changes to `main` make it harder to validate a coherent change set before it becomes part of the stable baseline. Database migrations also require local verification against PostgreSQL before they are accepted.

Documentation and automated tests must evolve together with the implementation so that architecture decisions and current behaviour remain traceable.

## Decision

All non-trivial changes are developed on a dedicated branch created from the current `main` branch.

The normal workflow is:

1. create a focused branch from an up-to-date `main`;
2. implement the complete change on that branch;
3. update relevant documentation in the same branch;
4. add or update tests for the changed behaviour;
5. generate and inspect Alembic migrations when persistence changes;
6. run the change locally against PostgreSQL;
7. require the complete local test suite to pass with zero warnings;
8. only then merge the validated branch into `main`;
9. verify the resulting `main` commit and CI status.

`main` is treated as the tested integration baseline. Direct commits to `main` are not part of the normal development flow.

## Continuous integration

GitHub Actions provides an independent verification layer.

The API CI workflow must:

- run on branch pushes and pull requests targeting `main`;
- use Python 3.13;
- start a PostgreSQL service compatible with the development database;
- install the API including development/test dependencies;
- apply all Alembic migrations from an empty database;
- run `alembic check` to detect model/schema drift;
- run the full API pytest suite;
- fail on Python warnings because pytest is configured with `filterwarnings = ["error"]`.

CI complements local validation. It does not replace the requirement to test database changes locally before merging.

## Documentation policy

A functional checkpoint is incomplete when implementation materially changes the domain or architecture but the corresponding documentation remains stale.

Relevant domain documents, ADRs, architecture documents and repository status documentation should therefore be updated as part of the same branch whenever applicable.

## Consequences

Benefits:

- `main` remains a validated baseline;
- regressions are caught before integration;
- migrations are tested both locally and from a clean CI database;
- documentation stays aligned with implementation;
- each domain increment has a reviewable and reversible history.

Costs:

- changes require an additional branch and validation step;
- database-related work requires both local PostgreSQL and CI verification;
- documentation is part of the definition of done rather than a later cleanup task.
