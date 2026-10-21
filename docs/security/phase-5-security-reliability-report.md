# Phase 5 Security and Reliability Report

**Status:** Code review and local regression checks complete. Operational backup/restore and load exercises remain blocked pending an isolated test environment and PostgreSQL backup utilities. This report does not certify production readiness.

**Scope:** Review of the Django settings and implemented `accounts`, `access_control`, `content`, `exam_engine`, and `config` code against the approved architecture and requirements. No live service was contacted. No production data was used.

## Findings and actions

| Severity | Finding | Evidence and action | Status |
| --- | --- | --- | --- |
| High, deployment gate | TLS termination requires an explicit trusted proxy boundary. Without proxy scheme handling, HTTPS redirects can loop behind a TLS-terminating Nginx; trusting a client-controlled forwarding header would also be unsafe. | Production settings now use `SECURE_PROXY_SSL_HEADER`. The deployment must expose Gunicorn only to Nginx and configure Nginx to overwrite `X-Forwarded-Proto`; never trust this header from direct clients. | Code configured; deployment topology remains unverified. |
| Medium | HSTS was absent in production settings. | Set `SECURE_HSTS_SECONDS` to one year and `SECURE_REFERRER_POLICY` to `same-origin`. HSTS subdomain coverage and preload remain off until all hostnames and HTTPS operations are confirmed. | Fixed in code; deploy check reports intentional HSTS subdomain/preload warnings. |
| Medium, launch gate | No demonstrated PostgreSQL backup restoration or recovery objective. | No `pg_dump` or `pg_restore` executable was available in PATH or the checked PostgreSQL 18 installation location. No backup was created and no restore was attempted. The safe procedure is in “Backup and restore exercise”. | Blocked; do not treat backups as recoverable until rehearsed. |
| Medium, launch gate | No measured workload baseline or capacity evidence. | Owner confirmed no staging environment. A load test was not run against the developer database or local runserver. The workstation had approximately 2.4 GB free memory during review, and the repository contains no deployed Nginx/Gunicorn target. | Blocked; no supported user/concurrency claim. |
| Low, operational | Sensitive authentication and exam write routes have no application-level rate limiter. | No limiter/dependency was added: deployment edge configuration and expected traffic are not yet established, and an in-process throttle would not coordinate across workers. Configure and verify edge limits for login/registration and exam writes before public launch; review false-positive and shared-IP behavior. | Open deployment action. |

No critical code-level finding was identified in the reviewed request paths. The open deployment gates above are material and prevent a production-ready conclusion.

## Reviewed controls

- **Authentication/session/CSRF:** Django auth, password hashing and validators, session middleware, CSRF middleware, protected account views, and POST-only logout/state-changing exam operations are in use. Registration creates ordinary users and does not accept staff/group permissions. No custom auth system was found.
- **Authorization:** Account data and attempt queries are owner-scoped. Attempt IDs are not treated as secrets. The shared entitlement policy fails closed. Admin is protected by Django staff and model permissions.
- **Exam integrity:** Start, save, load and submit services use server time, transactions, and row locking; the database enforces the one-active-attempt and response uniqueness invariants. Expiry is finalized when observed; retries return the existing terminal result. Scoring is server-side. Active exam rendering does not include correctness flags; result review happens after finalization.
- **File access:** Public PDF delivery checks publication and public visibility and sends private/no-store cache headers. Restricted files return 404. Media storage has no Django public media route. Production Nginx must not map `MEDIA_ROOT` to a public static directory. PDF signature/type/size validation is performed in the admin form path; files are not malware-scanned.
- **Queries and input:** Public listings and attempt history are paginated; exam question/option reads use `select_related`/`prefetch_related`; answer IDs are validated against the attempt's test and question. Existing publication and exam indexes were inspected. Query counts and production-scale latency have not been benchmarked.
- **Errors/logs:** Reviewed code contains no password/token logging or debug prints. Error responses for missing/unauthorized attempt and file objects are not-found responses. Production requires `DEBUG=False`; operational log configuration and centralized monitoring are not implemented.
- **Database integrity/failures:** Constraints and service transactions cover core lifecycle invariants. Existing tests cover expiry, retries, owner isolation, answer saving, scoring, and answer-key visibility. A real database outage, interrupted worker/process, and restore failure have not been exercised; request-level failure recovery remains an operational validation item.

## Verification evidence

Commands run from the repository root with the ignored local `.env` loaded into the process without printing its values:

- `python manage.py check` — passed, no issues.
- `python manage.py check --database default` — passed, database connectivity/configuration checked.
- `python manage.py makemigrations --check --dry-run` — passed, no changes detected.
- `python manage.py test accounts access_control content exam_engine config` — passed, 42 tests; Django created and destroyed its temporary PostgreSQL test database. Two failure-injection cases confirm answer-save and result-finalization transactions leave no partial state when a simulated `DatabaseError` occurs.
- `python manage.py check --deploy` — production settings loaded with process-only placeholder secret/host values. HSTS-not-set warning is resolved. The remaining findings are intentional: HSTS is not extended to unverified subdomains and preload is not enabled. A synthetic placeholder is not evidence that a real production secret meets strength requirements.

An initial attempt with the system Python failed because Django was not installed there; rerunning with the repository `.venv` succeeded. No dependency was installed or changed. No migrations were generated or applied. Failure injection checks transaction rollback, but it does not simulate a real server/process crash or network partition.

## Backup and restore exercise

Do not run this against a developer, staging-with-real-data, or production database. Once a disposable PostgreSQL target and PostgreSQL client utilities are available:

1. Create a synthetic database with representative schema and synthetic content/attempt records; record table counts and a checksum/known-answer query.
2. Create a custom-format backup with `pg_dump -Fc` using a least-privilege backup role. Protect the backup with restricted storage access and encryption at rest; do not put credentials in command history or the repository.
3. Restore into a newly created disposable database with `pg_restore`, not over the source database. Verify migrations, table counts, representative content, attempt state/scores, and application connectivity.
4. Record backup duration/size, restore duration, validation results, and achieved recovery point/time. Repeat after schema or deployment changes and regularly thereafter.
5. Define retention, failure alerts, key rotation, and a separate failure domain before operating backups as a recovery control.

This is a proposed procedure only. It has not been executed, and no recovery-time or recovery-point objective has been demonstrated.

## Load-test plan

Run only against an isolated, explicitly authorized staging deployment with synthetic accounts and records. Before testing, fix a target environment, test duration, request mix, acceptance thresholds, and a stop condition. Confirm that mail, payment, analytics, or other external side effects are disabled or sandboxed.

Model an examination session with realistic think time: authenticate; browse test details; start/resume; load question pages; change answers; autosave at a measured cadence and after changes; submit once; then open results/history. Include reconnect/retry behavior, a cohort reaching deadlines, and a controlled small burst of simultaneous submissions. Do not have all virtual users submit simultaneously except for the explicit burst scenario.

Progress only when each stage is healthy: 100, 500, 1,000, 2,500, then at most 5,000 virtual users if earlier results and staging capacity justify continuing. At each stage record virtual users and active request concurrency separately, request rate, p50/p95/p99 latency by route, error/timeout rates, autosave/submission correctness, CPU, memory, PostgreSQL CPU/memory/active and waiting connections, connection pool behavior, slow queries, disk, and test duration. Capture configuration, dataset size, tool/version, scripts, and raw results for reproducibility. Stop for integrity errors, sustained resource saturation, growing connection waits, or error/latency thresholds defined before the run.

No load tool or staging target was available/authorized for this exercise. Do not infer capacity from the budget target, a virtual-user count, or these plans.

## Remaining risks and next actions

1. Provision an isolated staging environment with Nginx/Gunicorn/PostgreSQL, restricted network paths, synthetic data, and a documented teardown process.
2. Install/use PostgreSQL client utilities in that environment; execute and record backup/restore rehearsal before launch approval.
3. Configure Nginx to overwrite `X-Forwarded-Proto`, restrict Gunicorn ingress to the proxy, exclude `MEDIA_ROOT` from direct serving, and verify TLS, allowed hosts, secure cookies, and redirects with real deployment hostnames.
4. Add edge rate limits for authentication and high-impact exam endpoints and observe expected student/shared-network traffic.
5. Define monitoring, log retention/access, alert thresholds, incident response, and performance/recovery objectives; then execute the documented load plan.
6. Consider upload malware scanning and request/body limits before accepting public uploads or increasing the current administrator-upload use.

No database schema change is proposed. Payment processing, private-file delivery, monitoring infrastructure, deployment automation, and load-test tooling remain outside this validation change.
