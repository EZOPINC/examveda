# Initial Architecture

**Status:** Approved baseline; Phase 2 free-content implementation complete and owner-approved on 2026-10-15 after local PostgreSQL 18.6 verification.
**Scope:** Planning baseline for the WBPSC Mock Exam Platform.

## Goals and constraints

The platform will provide free learning resources, timed mock examinations, student accounts and attempt history, administration, and a path to future memberships and paid tests. It must work on mobile devices and slower connections. The application interface and mock exams support English, Hindi, and Bengali; free study-material and previous-year-question content remains limited to its existing English/Bengali editorial workflow.

The initial technology baseline is Python 3.13, Django 5.2.18 LTS, Psycopg 3.3.6, PostgreSQL, Django templates, HTML, CSS, vanilla JavaScript, Nginx, Gunicorn, OCI, and Git. Exact Python package pins are recorded in `requirements.txt`; rationale and official version references are in [Decision 0002](docs/decisions/0002-runtime-versions.md). The INR 5,000–15,000 monthly infrastructure figure is a planning target, not a guaranteed cost or capacity. Review supported versions and security updates deliberately; do not silently change major versions.

## Application architecture

Use a modular Django monolith. Keep request handling, business rules, and persistence in the server application. Use templates for rendered pages and JavaScript for browser interactions such as timer display and autosave. PostgreSQL is authoritative for accounts, content state, questions, tests, attempts, responses, and entitlements.

The reserved Django project package is `config`. Preserve these planned entry points: `config.settings` with `base.py`, `development.py`, and `production.py`; `config/urls.py`; `config/wsgi.py`; `config/asgi.py`; `manage.py`; `.env.example`; and `requirements.txt`.

Canonical application boundaries are reserved as follows. Create an application only when its feature is in scope; do not create empty applications to fill out this list.

| Application | Responsibility | Initial timing |
| --- | --- | --- |
| `accounts` | Registration and account self-service using Django's built-in user model | Phase 4; no custom user or profile model |
| `content` | Subjects, topics, public learning resources and publishing | Free content phase |
| `exam_engine` | Questions, tests, attempts, responses, timers, scoring and permitted review | Exam engine phase |
| `access_control` | Shared public/restricted access decision and future verified entitlement lookup | Phase 4; policy service only, no entitlement storage |
| `payments` | Payment transactions, memberships and provider integration | Future paid-access phase |
| `file_delivery` | Authorization-gated protected files | When protected file delivery is required |

### Exam engine modules (Phase 3)

Implemented modules are `exam_engine.models` (six core exam entities plus `QuestionTranslation`, `QuestionOptionTranslation`, and `MockTestTranslation`), `exam_engine.services` (atomic lifecycle, locale-completeness checks, and score operations), `exam_engine.views` and `exam_engine.urls` (public descriptions, language selection, and authenticated attempt requests), `exam_engine.forms` (Django admin inline validation), `exam_engine.admin` (staff authoring, locale preview/completeness, and read-only attempt inspection), `exam_engine.apps` (Django registration), `exam_engine.tests` (lifecycle, locale, and permission coverage), and additive `exam_engine.migrations.0002_mocktest_instructions_mocktest_language_and_more` (language-aware schema). Templates live under `templates/exam_engine/`; browser behavior and styling are `static/exam_engine/exam.js` and `exam.css`. Django UI catalogs live under `locale/hi/` and `locale/bn/`. Keep these names and responsibilities stable. Do not add parallel modules or duplicate models; a new module requires an approved requirement that the existing responsibilities cannot reasonably own. Do not introduce `accounts`, `access_control`, or `payments` in this phase.

### Mock-exam language handling

Question prompts, option labels, and explanations use translation rows owned by `exam_engine`; stable `QuestionOption` rows remain the shared option identities and correctness key. A test stores one source language and may have localized metadata. The service advertises and starts only a language with published, complete test metadata and all required question, option, and (when present in the source) explanation text. The attempt stores its selected language; switching changes only presentation and preserves its timer, response identities, and score key. Translation wording and test wording freeze with the existing exam graph after the first attempt. Existing test language is nullable and must be reviewed and assigned by staff rather than inferred; attempted question/test graphs stay frozen, while unused tests can be reviewed before assignment. Free-content models and previous-year question papers are not expanded with Hindi content by this decision.

### Implemented content modules

| Module | Responsibility |
| --- | --- |
| `content.models` | Approved exam/subject taxonomy, editorial page lifecycle, resource classification and PDF metadata. |
| `content.forms` | Admin server-side validation of taxonomy relationships, publication state and PDF upload constraints. |
| `content.views` | Published listings/detail pages, staff-only preview and published-public PDF streaming. |
| `content.urls` | Namespaced approved public archive and detail routes plus preview/file routes. |
| `content.admin` | Staff editing, classification inline, preview link, publication controls and file visibility administration. |
| `content.tests` | PostgreSQL-backed route, rendering, publication and preview boundary tests. |

The blog extends `content.models.ContentPage` with optional blog category, byline, and featured-image fields; `BlogCategory` is the editorial taxonomy because exam `Topic` is scoped to subject content. `content.views`/`content.urls` own public blog pages and publication-checked image delivery, while `content.sitemaps` lists only public articles and non-empty categories. `config.views.social_links_context` exposes validated optional HTTPS profile URLs from deployment configuration. Keep blog content in this existing content boundary; do not create a parallel blog app or content table.

### Accounts and access modules (Phase 4)

`accounts.apps`, `accounts.forms`, `accounts.views`, `accounts.urls`, and `accounts.tests` implement student registration, owner-only account details, password changes, and authorization regression coverage using Django's existing user model. Templates are in `templates/accounts/`; the existing `templates/registration/login.html` remains the login page. Do not add a custom account model, profile table, reset-email flow, or role framework without an approved requirement. Lost-password recovery is administrator-assisted until verified email recovery and mail delivery are approved.

`access_control.apps`, `access_control.services`, and `access_control.tests` provide the shared `user_can_access()` and `user_has_entitlement()` boundary used by exam availability and public file delivery. The current entitlement lookup always denies; payment and entitlement records remain future work. Do not create parallel access modules or entitlement tables in Phase 4.

The app also uses its standard `apps.py` registration, migration package, templates under `templates/content/`, and stylesheet `static/content/content.css`. It does not create a separate file-delivery app; restricted file delivery remains deferred.

Use Django `auth` and `admin`; do not duplicate them. Keep business logic out of templates. Add standard modules such as `services.py`, `selectors.py`, or `permissions.py` only when a real feature needs the responsibility. Do not introduce React, microservices, Kubernetes, Redis, Celery, or other infrastructure without a documented requirement and evidence.

## Data ownership and consistency

The preliminary entities and relationships are described in [the data model requirements](docs/requirements/data-model.md). Keep the canonical names in that document stable once implementation begins. Use Django's normal primary keys, explicit foreign keys, transactions for multi-step state changes, and database constraints for invariants that must hold under concurrent requests.

Question and test editing must not silently change the meaning of an existing attempt. Decision 0004 selects graph immutability after an attempt starts; editors create new Question and MockTest records for revisions. Revisit version/snapshot entities only if editorial evidence shows that creating new records is error-prone or fails a required historical reporting workflow.

## Public and protected boundaries

Publicly published resources and public test descriptions have stable, lowercase, hyphenated URLs. Draft and unpublished content must not be exposed. Student attempt operations require authentication and server-side ownership checks. Correct answers and explanations are returned only when the test's review policy permits them.

Public educational files may use public object storage. Protected files require authorization before delivery; a hidden link is not protection. If object storage is used for protected files, authorize first and use short-lived access. Avoid shared caching for user-specific or permission-sensitive responses unless a tested cache key and invalidation policy exist.

## Exam authority

The server is authoritative for attempt ownership, state, allowed duration, expiry, submitted time, answer keys, and score. Record start and expiry timestamps on the server. A browser timer is only a display aid. Autosave and submission must verify the authenticated owner and valid state. Submission must be retry-safe, and score calculation must not trust client input. The lifecycle and scoring policy are defined in the functional requirements.

## Security baseline

Use Django password hashing, sessions, CSRF protection, validation, and permissions. Enforce authorization for every restricted object and action. Keep production secrets outside source control and use secure host, HTTPS, and cookie settings in production. Keep the database private. Do not log passwords, session identifiers, tokens, or unnecessary personal data. Review dependencies through controlled, tested updates.

See [security requirements](docs/requirements/security-requirements.md) for the planning checklist and phase gates.

## Deployment and operations

Deploy on Linux OCI infrastructure with Nginx in front of Gunicorn and Django. Keep PostgreSQL private. The Phase 6 pilot deployment plan uses one Ubuntu LTS compute instance with PostgreSQL bound to loopback, Nginx on ports 80/443, and Gunicorn on loopback; private OCI Object Storage holds off-server database and media backups. This single-host shape is not highly available, and it remains subject to cost, capacity, restore, monitoring, and security validation. See [the deployment guide](deploy/README.md). A managed or separate database may be preferable if its verified cost fits the target and its reliability benefits justify it.

Use environment-provided secrets, HTTPS, automated PostgreSQL backups to OCI Object Storage where appropriate, defined retention, and restore rehearsals. Monitor host and application health, errors, disk, database capacity, and backup completion. Measure traffic and slow queries before adding caching, Redis, Celery, a CDN, multiple application hosts, or a separate database host. Detailed phase gates are in [the development roadmap](DEVELOPMENT_ROADMAP.md).

## Naming and change control

`PROJECT_AI_RULES.md` and `AGENTS.md` govern future work. Before each phase, inspect the repository, Git status, and relevant documentation. Reuse established modules, names, fields, URLs, configuration keys, and patterns. Do not rename, replace, or refactor working components without an explicit reviewed reason and approval. Do not add a module, variable, dependency, framework, or infrastructure component merely for convention or speculation. When a feature truly needs a new one, document its responsibility and why an existing component cannot own it; update the decision and requirements documents as needed. Preserve all pre-existing user changes.

## Decisions to revisit with evidence

| Decision | Starting choice and reason | Evidence to justify change |
| --- | --- | --- |
| Application style | Modular Django monolith for a small team and cohesive workflows | Measured deployment or scaling constraints that cannot be addressed within the monolith |
| Front end | Django templates and vanilla JavaScript for low complexity and broad device support | Accessibility, interaction, or measured performance requirements that templates cannot meet |
| Database | PostgreSQL as authoritative relational store for attempts and constraints | Verified workload or managed-service constraint with a reviewed migration path |
| Hosting shape | Begin with the simplest OCI Linux deployment that fits verified reliability and budget | Load, recovery objectives, operational risk, or actual pricing justifies service separation |
| Background jobs/cache | None initially, to avoid operating unused services | Measured need for asynchronous work or caching with a safe invalidation design |
| Account model | Use Django's built-in user model for the foundation; no custom account behavior is confirmed | Confirmed product requirements that require custom authentication identity fields, with a reviewed migration and maintenance plan before account features are built |
| Test history | Freeze the question/test graph at first attempt; use new Question and MockTest records for revisions, avoiding version/snapshot/result tables | Demonstrated editorial errors or a required historical audit/reporting workflow that cannot be met by the frozen graph |
| Exam languages | Store localized prompt/option/explanation and test metadata beside one logical exam graph; keep stable option rows and correctness shared | Evidence that translation completeness, language-specific editing, or reporting needs cannot be met safely by the approved translation relationships |

## Related documents

- [Development roadmap](DEVELOPMENT_ROADMAP.md)
- [Functional requirements](docs/requirements/functional-requirements.md)
- [Data model requirements](docs/requirements/data-model.md)
- [Security requirements](docs/requirements/security-requirements.md)
- [Decision record 0001](docs/decisions/0001-initial-architecture.md)
- [Decision record 0007: multilingual mock exams](docs/decisions/0007-multilingual-mock-exams.md)
