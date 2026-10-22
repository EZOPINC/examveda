# Changelog

Notable project changes are recorded here.

## 2026-10-22 — English, Hindi, and Bengali mock exams

- Added `QuestionTranslation`, `QuestionOptionTranslation`, and `MockTestTranslation` in `exam_engine`; stable option rows and one shared correctness key continue to drive scoring. Migration `exam_engine.0002` is additive and leaves legacy test/attempt language fields nullable for staff review.
- Added complete-language availability checks, explicit language selection before start, attempt-level language persistence/switching, localized active/review views, and staff translation preview/completeness controls. Incomplete or unpublished language variants are not listed, started, or newly selected.
- Added Django interface catalogs for Hindi and Bengali with compiled runtime catalogs, shared language controls, account/home and mock-exam UI translations, and local script-font fallbacks. Free previous-year-paper text/PDF workflow remains unchanged and does not receive Hindi translations.
- Added regression coverage for language completeness, publication, shared correctness, answer/timer preservation during switching, localized rendering, legacy-safe locale handling, and source-question publication. No app, dependency, payment, PDF, or production-data change.

## 2026-10-22 — Blog and social integration

- Added public blog index, category and article routes using the existing `ContentPage` editorial lifecycle, plus a dedicated editorial `BlogCategory` and optional author/featured-image fields in additive migration `content.0002`.
- Added staff-only draft image preview and publication-checked public image delivery with size/type/signature validation, canonical/SEO/Open Graph metadata, published-only Article JSON-LD and sitemap entries.
- Added configurable HTTPS-only Facebook, Instagram, Telegram and YouTube footer links, plus accessible browser share/copy controls on blog and free study-material pages.
- Added regression coverage for publishing boundaries, structured-data escaping, image access and social link safety. No new dependency or frontend framework.

## 2026-10-22 — Application-wide UI and SEO refresh

- Added a shared responsive Django base template with consistent navigation, skip link, footer, typography, controls, cards, breadcrumbs, forms, and page metadata.
- Reworked home, study-material, mock-test, account, result, error, and examination templates while retaining named URLs, form actions, access checks, content fields, and exam JavaScript hooks.
- Added unique public page titles/descriptions, canonical URLs, Open Graph tags, and public/private `robots` policies; staff previews use generic SEO metadata and are marked `noindex`.
- Added regression assertions for public metadata and private-page indexing. No model, migration, dependency, URL, or runtime setting changes.

## 2026-10-22 — OCI admin database diagnosis

- Documented that Django admin and application data share the single PostgreSQL `default` alias; there is no admin-only SQLite connection or database router.
- Added safe OCI runbook steps to inspect Gunicorn's effective database identity and account flags, and to create/reset an administrator using the exact runtime EnvironmentFile.
- Added troubleshooting guidance. The live OCI cause remains unconfirmed until the instance's runtime database identity and user flags are checked by an authorized operator.
- No application settings, database data, credentials, or production infrastructure were changed.

## 2026-10-21 — Phase 6 OCI deployment preparation

- Added a pinned Gunicorn dependency and initial systemd/Nginx configuration for a single-host pilot, with Gunicorn and PostgreSQL limited to loopback and no public media alias.
- Corrected `STATIC_URL` to `/static/` so assets on nested public pages resolve through the planned Nginx static alias; added a regression check.
- Added a private-bucket Object Storage backup job for PostgreSQL and uploaded media using instance-principal authentication, plus deployment, migration, restore, monitoring, smoke-test, and rollback procedures.
- No OCI resources were provisioned. A successful backup restore, live TLS/proxy checks, monitoring alerts, and authorized load validation remain launch gates.

## 2026-10-21 — Local demo navigation diagnosis

- Added the existing public Free Study Materials link to the standalone home-page navigation; the root template did not render a shared navigation component.
- Confirmed this local Django invocation uses fallback SQLite because PostgreSQL environment variables are absent from its process; `.env` is not loaded automatically. Django tests use a separate temporary database. Loaded demo records explicitly into the confirmed local SQLite database with the existing safe seed command.
- Added a regression assertion that the home page renders the public navigation link. No model, migration, dependency, or database configuration changes.

## 2026-10-21 — Phase 5A free study-material demo navigation

- Reused the existing content taxonomy and publication models to add exam → subject → previous-year paper browsing while retaining the `/free-resources/` root and existing stage/year routes.
- Added a `DEBUG=True`-only, conflict-safe `seed_demo_study_materials` command for two exams, six exam/subject mappings, and twelve published demo papers with original illustrative questions; repeated runs are idempotent.
- Added responsive breadcrumb/detail pages and explicit demo notices. No PDF, application, dependency, model, or migration was added.
- Added command, relationship, publication, routing, ordering, and rendering tests. Phase 5 operational security/reliability gates remain open.

## 2026-10-20 — Phase 5 security and reliability review

- Owner confirmed approval of Phases 3 and 4 and authorized Phase 5.
- Added production HSTS, same-origin referrer policy, and the Nginx TLS-termination proxy setting. The deployment boundary must prevent direct/untrusted clients from supplying `X-Forwarded-Proto`.
- Added transaction failure-injection regression coverage for answer persistence and submission finalization rollback.
- Detailed review evidence, severity-ranked findings, verification results, and blocked operational exercises are recorded in [the Phase 5 report](docs/security/phase-5-security-reliability-report.md).
- No migrations, dependencies, backup/restore execution, or load tests were added/performed. No authorized staging environment or PostgreSQL backup utilities were available; production readiness is not claimed.

## 2026-10-20 — Phase 4 accounts and access implementation

- Owner explicitly authorized Phase 4. Phase 3 approval was later explicitly confirmed on 2026-10-20.
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
