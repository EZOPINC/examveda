# WBPSC Mock Exam Platform — Global AI Development Rules

## 1. Project mission

Build a maintainable, secure, mobile-friendly, affordable WBPSC examination preparation platform that provides:

- Free study materials, notes, previous-year questions, solutions, and educational articles.
- Timed mock examinations and practice tests.
- User registration, authentication, and attempt history.
- Future paid tests, memberships, and payment integration.
- An administrative interface for managing content, questions, tests, and users.
- A deployment path that supports increasing traffic without requiring an unnecessary rewrite.

The application must be suitable for learners using desktop computers, mobile devices, slower connections, and Bengali or English educational content.

## 2. Technology baseline

Use the following technologies unless a documented technical constraint requires a change:

- Backend: Python and Django.
- Database: PostgreSQL.
- Web server: Nginx.
- Application server: Gunicorn.
- Frontend: Django templates, HTML, CSS, and vanilla JavaScript.
- Hosting: Oracle Cloud Infrastructure (OCI).
- Public files and backups: OCI Object Storage where appropriate.
- Version control: Git.
- Testing: Django testing tools and automated tests.
- Deployment: Linux-based environment.

Do not introduce React, Kubernetes, microservices, or additional infrastructure solely because they are popular or available.

Redis, Celery, a CDN, separate database servers, and load balancing may be introduced later when requirements, measurements, or operational needs justify them.

Use supported, mutually compatible stable software versions. Record the chosen versions in the repository and dependency files. Do not silently upgrade major versions.

## 3. Architecture rules

Use a modular Django monolith.

Keep related business functionality in clearly separated Django applications. Applications may share data through explicit model relationships and well-defined service functions.

Keep business logic out of templates. Keep database operations and scoring logic on the server. Use JavaScript for browser interactions, timers, autosave requests, and other interface behavior.

PostgreSQL is the authoritative data store for accounts, questions, tests, attempts, answers, and permissions.

Public educational content must be accessible through stable, SEO-friendly URLs. Public content and restricted content must have separate access rules.

Do not build a generic framework before a working feature requires it. Prefer the simplest maintainable solution that meets the current requirements.

## 4. Canonical Django application names

Use these names as the initial application boundaries:

- `accounts` — authentication, user profiles, and account-related behaviour.
- `content` — educational pages, study materials, subjects, and topics.
- `exam_engine` — questions, mock tests, attempts, responses, timers, scoring, and permitted result review.
- `access_control` — reusable access policies and content/test entitlement checks.
- `payments` — future payment transactions, membership purchases, and payment provider integration.
- `file_delivery` — authorized delivery of protected files and documents.

Create only the applications needed for the current phase. The names above are reserved canonical names, not permission to create unused or empty applications.

Use Django's built-in `auth` and `admin` applications rather than duplicating their functionality.

If an application must be renamed, split, merged, or replaced, first explain the reason, impact on imports, migrations, database tables, URLs, tests, and deployment. Obtain explicit approval before proceeding.

## 5. Canonical configuration and entry points

Preserve these names unless an approved architectural change requires otherwise:

- Django project package: `config`
- Settings package: `config.settings`
- Base settings: `config/settings/base.py`
- Local development settings: `config/settings/development.py`
- Production settings: `config/settings/production.py`
- Root URL configuration: `config/urls.py`
- WSGI entry point: `config/wsgi.py`
- ASGI entry point: `config/asgi.py`
- Django management entry point: `manage.py`
- Environment variable template: `.env.example`
- Python dependency file: `requirements.txt`

Keep secrets out of source control. `.env.example` contains placeholder values only. Production secrets must be provided through the deployment environment or an appropriate secrets-management mechanism.

Do not commit real passwords, API keys, database credentials, private keys, or production environment files.

## 6. Canonical module conventions

Within each Django application, use Django's standard module names when applicable:

- `models.py` — persistent data models.
- `views.py` — HTTP request handling.
- `urls.py` — application URL patterns.
- `admin.py` — Django admin registration and customization.
- `forms.py` — Django forms and input validation.
- `tests.py` or a `tests/` package — automated tests.
- `services.py` — business operations that should be reusable outside a view.
- `selectors.py` — reusable read/query operations when query complexity warrants it.
- `permissions.py` — application-specific authorization rules.
- `constants.py` — stable shared constants.
- `tasks.py` — background jobs, only if a background task system is introduced.

Do not create every possible module automatically. Start with the modules needed for the feature and introduce new modules when they improve clarity or reuse.

If a module grows too large, propose a split based on clear responsibilities. Do not rename modules simply to match a personal preference.

## 7. Naming conventions

### Python

- Modules and packages: `snake_case`
- Functions and variables: `snake_case`
- Classes and Django models: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private implementation helpers: leading underscore where appropriate.
- Boolean variables: descriptive names such as `is_active`, `has_access`, and `can_resume`.

Examples:

- `calculate_exam_score()`
- `submit_test_attempt()`
- `QuestionOption`
- `TestAttempt`
- `MAX_ATTEMPT_DURATION_MINUTES`

### Django models and fields

Use singular `PascalCase` model names, such as `MockTest` and `AttemptResponse`.

Use descriptive `snake_case` fields, such as `started_at`, `submitted_at`, `is_published`, and `time_limit_minutes`.

Use Django's standard primary key behaviour unless a documented requirement justifies a different strategy.

Do not change existing model or field names after migrations have been applied without assessing the migration and data-preservation impact.

### URLs

Use lowercase, hyphen-separated public URL slugs where appropriate.

Examples:

- `/free-resources/`
- `/free-resources/wbcs/`
- `/free-resources/wbcs/prelims/2024/`
- `/mock-tests/`
- `/mock-tests/wbcs-prelims-practice/`

Use descriptive Django URL names such as `content:resource_detail` and `exam_engine:attempt_detail`.

Prefer named URL reversal over hard-coded internal URL strings.

### HTML and CSS

- HTML templates: `snake_case.html`
- JavaScript files: `snake_case.js`
- CSS files: `snake_case.css`
- CSS classes: descriptive kebab-case.
- HTML IDs: descriptive kebab-case.

Use consistent, reusable CSS class names. Do not introduce a new CSS framework or rename existing classes without a clear need.

### JavaScript

- Variables and functions: `camelCase`.
- Constructors/classes: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- DOM IDs and HTML data attributes: follow the established HTML conventions.

Use explicit, namespaced JavaScript initialization functions. Avoid polluting the global namespace.

### Database

Use descriptive singular Django model names and descriptive fields.

Let Django manage table and constraint names by default. Give custom indexes and constraints meaningful names when required.

Do not manually rename database tables, columns, indexes, or constraints without a reviewed migration plan.

### Tests

Name test files and test functions descriptively.

Examples:

- `test_user_cannot_view_another_users_attempt`
- `test_submitted_attempt_cannot_be_modified`
- `test_score_is_calculated_on_server`
- `test_unpublished_content_is_not_publicly_accessible`

## 8. Required code documentation

Every new Python module must begin with a module docstring explaining:

1. What the module is responsible for.
2. Why the module exists in the architecture.
3. Which components or modules depend on it, where useful.
4. Any important security, performance, or extension considerations.

Every class and public business function must have a docstring explaining its purpose. Document non-obvious arguments, return values, exceptions, and side effects.

Every substantial code section must include a concise comment explaining why the section exists, particularly where future maintenance could be difficult.

For important decisions, explain the reason rather than restating the code.

Examples:

- Why a score is calculated on the server.
- Why an attempt submission is idempotent.
- Why a query uses `select_related()` or `prefetch_related()`.
- Why a database constraint is needed in addition to form validation.
- Why a file is served through an authorization check.
- Why a transaction uses `atomic()`.
- Why a timer uses server-recorded timestamps.

Do not add comments to every line or produce comments that merely repeat the statement beneath them. Comments must improve future troubleshooting, operational understanding, or safe extension.

When changing existing code, add or update comments if the underlying design or behaviour changes.

## 9. Database and migration rules

- Create migrations for model changes.
- Review migration operations before applying them to important environments.
- Never delete or recreate a database as a routine troubleshooting step.
- Never use destructive migrations without explicit approval and a verified backup.
- Preserve existing data when renaming or restructuring fields.
- Use database constraints for important invariants where appropriate.
- Use transactions for multi-step operations that must succeed or fail together.
- Avoid N+1 queries and unnecessary database calls.
- Do not store sensitive data without a clear business need and appropriate protection.

Before applying migrations in production, provide the migration plan, backup requirement, rollback considerations, and verification steps.

## 10. Security rules

- Use Django's built-in authentication, CSRF protection, password hashing, and permission facilities.
- Validate all server-side input.
- Enforce authorization on the server for every restricted object and action.
- Never trust client-provided scores, prices, permissions, attempt ownership, or submission timestamps.
- Do not expose correct answers before the test's configured review point.
- Do not expose one user's private attempt data to another user.
- Keep database access private.
- Use HTTPS in deployed environments.
- Use secure production cookie and host settings.
- Avoid logging passwords, session identifiers, tokens, or unnecessary personal data.
- Keep dependencies updated through controlled, tested changes.

For protected documents, check authorization before delivering the file. Do not assume that hiding a download button protects a public URL.

## 11. Exam-engine integrity

The server is authoritative for exam duration, attempt state, scoring, answer keys, and submission status.

Use server-recorded timestamps for duration enforcement. Browser timers are visual aids, not security controls.

Autosave and submission endpoints must verify the authenticated user's ownership of the attempt.

Design retryable operations to avoid duplicate submissions or duplicate results. Use database transactions and uniqueness constraints where appropriate.

Define and test the permitted attempt lifecycle before implementing complex behaviour.

Do not reveal correct answers, scoring keys, or private test content through hidden HTML, JavaScript variables, API responses, or client-side source files before they are permitted.

## 12. Performance rules

Start with efficient Django queries, sensible pagination, database indexes where justified, and caching only where it is useful and safe.

Do not introduce Redis, Celery, multiple application servers, or a separate database server solely in anticipation of scale.

Measure before optimizing. When a performance issue occurs, identify the slow request or query and gather evidence before proposing a fix.

Never cache user-specific or permission-sensitive responses in a shared cache without an explicit, tested cache-key and invalidation strategy.

## 13. Phase and change-control rules

Work on one requested phase or task at a time.

Before implementation:

1. Read this file and the relevant architecture/roadmap documents.
2. Inspect the existing repository and Git status.
3. Identify the current phase and existing functionality.
4. List the files that need to be created or changed.
5. Identify risks, dependencies, migrations, and tests.
6. State any assumptions or ask a concise clarification question if a decision is blocking.

During implementation:

1. Make the smallest complete change.
2. Reuse existing names, patterns, and utilities.
3. Do not overwrite unrelated work.
4. Do not change architecture or naming conventions without approval.
5. Do not silently remove functionality.
6. Do not replace a working implementation with a new approach without a demonstrated reason.

After implementation:

1. Run relevant automated tests and checks.
2. Review migrations and configuration changes.
3. Report files created, modified, and deleted.
4. Explain how to run and verify the feature.
5. Update documentation and `CHANGELOG.md`.
6. Record unresolved issues and next steps.

If a tool cannot execute a check, say so clearly. Never claim that code passed a test that was not run.

## 14. Troubleshooting rules

When a problem is reported:

1. Capture the exact error, traceback, request, and reproduction steps.
2. Identify whether the problem is in configuration, code, dependencies, database state, permissions, infrastructure, or external services.
3. Inspect relevant files and recent changes.
4. Establish the likely root cause using evidence.
5. Propose the smallest safe fix.
6. Add a regression test when practical.
7. Run the relevant tests and checks.
8. Confirm whether the fix resolves the original symptom.
9. Document the cause, fix, and prevention steps in `TROUBLESHOOTING.md`.

Do not make unrelated refactors while fixing a defect. Do not suppress exceptions, disable security controls, or remove validation merely to make an error disappear.

If the root cause is uncertain, state what is known, what remains uncertain, and the next diagnostic step.

## 15. Completion report

At the end of every task, provide:

- Objective completed.
- Files created, modified, or deleted.
- Key implementation decisions.
- Commands executed.
- Tests run and their actual results.
- Database migration impact.
- Security or performance considerations.
- Manual verification steps.
- Known limitations or unresolved issues.
- The exact next recommended task.

Do not begin the next phase automatically. Wait for authorization.

## 16. Precedence and preservation

These rules remain active throughout the project.

Existing approved architecture and naming conventions take precedence over new suggestions from the AI.

If a requirement conflicts with this baseline, stop and explain the conflict before changing the baseline.

An approved change must be documented in `docs/decisions/` and reflected in the relevant project documents.

Never rename, remove, relocate, or replace an established module, function, class, variable, URL, database field, or configuration key merely to improve style. Make such changes only when necessary, reviewed, and explicitly approved.
