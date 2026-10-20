# Changelog

Notable project changes are recorded here.

## 2026-10-20 — Phase 4 accounts and access implementation

- Owner explicitly authorized Phase 4. Phase 3 implementation and verification are complete; its approval gate had not been separately recorded, so no separate Phase 3 approval is claimed.
- Added student registration, owner-only account details, Django password change, and regression tests without a custom user/profile model or additional dependency.
- Added the shared fail-closed `access_control` policy for public files and test availability. No entitlement or payment model, payment gateway, or restricted-file delivery was added.
- Recorded administrator-assisted lost-password recovery until verified email recovery and production mail delivery are approved.
- Verified locally against PostgreSQL: `check`, `check --database default`, `makemigrations --check --dry-run`, and the combined account/access/exam/content/config suite (40 tests passed). No Phase 4 migrations are pending; the built-in user schema is unchanged.

## 2026-10-20 — Phase 3 mock exam engine implemented

- Added the approved six-model exam domain and initial `exam_engine.0001_initial` migration for questions, options, tests, ordered test questions, attempts, and saved responses.
- Added staff authoring validation, test descriptions, authenticated start/resume, owner-scoped exam and result pages, CSRF-protected autosave, submission, expiry finalization, and server-side scoring.
- Paginated public test listings and student attempt history without adding a dependency.
- Added tests for valid/unauthorized starts, ownership, CSRF, response persistence, expiry, interrupted resumption, retry-safe submission, scoring, review visibility, and frozen exam content.
- Verified locally against PostgreSQL: `check`, `check --database default`, `makemigrations --check --dry-run`, and the combined exam/content/config suite (30 tests passed). `exam_engine.0001_initial` is applied locally; no model changes are pending. Phase 3 remains at the owner approval gate.

## 2026-10-20 — Phase 3 authorized

- Owner approved the exam-engine policy defaults recorded in Decision 0004 and authorized Phase 3 implementation.

## 2026-10-15 — Phase 2 approved

- Owner approved the completed Phase 2 free-content implementation and requirements.
- Recorded approval in the roadmap, architecture status, content decision, and requirements documents. Phase 3 remains unauthorized.

## 2026-10-15 — Phase 2 free educational content implemented

- Added the `content` app with the approved seven-model taxonomy, publication lifecycle, resource classification, and PDF metadata.
- Added paginated, responsive public listings and stable archive/detail URLs for categories, stages, years, resource types, subjects, topics, and editorial pages.
- Added Django admin draft editing, staff-only preview, publication/unpublication, and public/restricted PDF visibility controls.
- Public PDF streaming requires a published page and public file metadata; private media paths have no direct application route.
- Added PostgreSQL-backed coverage for public visibility, drafts, preview, rendering, and canonical URL reversal.
- Phase 2 verification completed locally; implementation approval is recorded above.

## 2026-10-15 — Phase 2 content model approved

- Approved the content taxonomy, page/resource/file metadata entities, and canonical public URL scheme in Decision 0003.
- Confirmed draft preview and public PDF delivery boundaries; restricted files remain private and unserved until an authorized delivery feature exists.

## 2026-10-15 — Phase 1 foundation

- Established the `config` Django project package with separated base, development, and production settings.
- Added the home page, low-information health endpoint, custom error templates, and initial HTTP tests.
- Pinned the Python/Django/PostgreSQL adapter baseline and documented local setup.
- Production settings now require explicit secrets, allowed hosts, and PostgreSQL environment variables.
- Verified local SQLite foundation migrations, three initial tests, static collection, and local HTTP smoke requests. Phase 2 also verified authenticated connectivity to local PostgreSQL 18.6.
