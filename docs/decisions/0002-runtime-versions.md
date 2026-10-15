# Decision 0002: Foundation Runtime Versions

- **Status:** Accepted for the Phase 1 baseline
- **Date:** 2026-10-15
- **Scope:** Python, Django, and PostgreSQL adapter versions

## Decision

- Target Python 3.13, installing its latest maintenance release for development and deployment. The execution environment used for initial verification reports Python 3.13.3.
- Pin Django to `5.2.18`, the current maintenance release in the Django 5.2 LTS series at the time of this decision.
- Pin `psycopg[binary]` to `3.3.6` for the PostgreSQL adapter and straightforward local installation across supported developer platforms.
- Keep exact Python package pins in the repository's `requirements.txt`. Review supported versions and security fixes as a planned dependency maintenance task; do not silently change major/minor baselines.

## Rationale

Django 5.2 is an LTS release with a longer support horizon than the current feature release line, while supporting Python 3.13. Choosing the LTS line reduces upgrade pressure for a new project. Psycopg 3 is the modern PostgreSQL adapter supported by Django. The binary extra avoids requiring a separate local libpq installation during initial Windows development; production packaging should be reviewed for the target Linux image before deployment.

## Evidence reviewed

- [Django 5.2 release notes](https://docs.djangoproject.com/en/5.2/releases/5.2/) identify 5.2 as LTS and document supported Python versions.
- [Django 5.2.18 release notes](https://docs.djangoproject.com/en/5.2/releases/5.2.18/) identify the current maintenance release at decision time.
- [Django database documentation](https://docs.djangoproject.com/en/5.2/ref/databases/#postgresql-notes) describes PostgreSQL support and Psycopg.
- [Psycopg on PyPI](https://pypi.org/project/psycopg/) identifies version 3.3.6 and supported Python classifiers.
- [Python 3.13.16 release page](https://www.python.org/downloads/release/python-31316/) records the latest 3.13 maintenance release available at decision time.

## Revisit criteria

Review the pins when a security fix, Django support deadline, Python lifecycle change, OCI operating-system constraint, or dependency compatibility issue warrants it. Update the dependency file, this record, setup documentation, and verification results together.
