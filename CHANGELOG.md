# Changelog

Notable project changes are recorded here.

## 2026-10-15 — Phase 1 foundation

- Established the `config` Django project package with separated base, development, and production settings.
- Added the home page, low-information health endpoint, custom error templates, and initial HTTP tests.
- Pinned the Python/Django/PostgreSQL adapter baseline and documented local setup.
- Production settings now require explicit secrets, allowed hosts, and PostgreSQL environment variables.
- Verified local SQLite migrations, three initial tests, static collection, and local HTTP smoke requests. PostgreSQL connectivity could not be verified because no service was available.
