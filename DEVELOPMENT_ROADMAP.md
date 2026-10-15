# Development Roadmap

**Status:** Phase 1 foundation implemented; PostgreSQL connectivity verification remains blocked by the unavailable local service. Each phase requires explicit authorization before work begins.

## Working rules for every phase

1. Read `AGENTS.md`, `PROJECT_AI_RULES.md`, this roadmap, and the relevant requirements and decision records.
2. Inspect Git status and the current implementation before editing; preserve unrelated and uncommitted changes.
3. Work only on the approved phase. Reuse existing modules and names. Propose new modules, variables, dependencies, or infrastructure only when a documented feature requirement needs them and existing components cannot own the work.
4. Before implementation, state intended file changes, risks, migrations, and verification. Avoid unrelated refactoring.
5. After authorized implementation, run relevant checks, inspect the diff, update applicable documentation and changelog, and report actual results. Never claim a check passed if it was not run.
6. Stop at the phase gate and wait for explicit approval before starting the next phase.

## Phases and gates

| Phase | Scope | Exit evidence / approval gate |
| --- | --- | --- |
| 0. Analysis and planning | Repository inventory, requirements, architecture and decision record | Owner reviews and approves these documents; no application code is part of this phase |
| 1. Foundation | Supported version selection, Django `config` foundation, environment configuration, database connection, initial account-model decision, baseline checks | Configuration and security settings reviewed; migrations reviewed before application; local setup documented; smoke checks recorded |
| 2. Free content | `content` models and public pages, publication workflow, language-aware content, stable public URLs | Published content is reachable, drafts are private, URL and mobile behavior verified |
| 3. Exam engine | `exam_engine` question/test authoring, attempt lifecycle, server-side timing, autosave, submission, score, permitted review | Lifecycle, boundary times, ownership, duplicate requests, scoring, and review permissions verified with automated tests |
| 4. Accounts and access | Registration/login, profile needs, history, shared policies where needed | Authentication, account recovery policy, ownership isolation, and entitlement decisions verified |
| 5. Security and quality | Cross-feature security review, accessibility, mobile/slow-network checks, performance baseline, backup/restore rehearsal, monitoring design | Findings and accepted risks documented; tests and measured performance evidence reviewed |
| 6. Deployment | OCI Linux deployment, Nginx, Gunicorn, PostgreSQL, HTTPS, secrets, backup/restore, monitoring, rollback | Deployment and restore runbooks exercised; production settings and readiness evidence approved |
| Future paid access | Membership and paid tests, `payments`, provider integration and relevant access rules | Provider callbacks, idempotency, reconciliation, refund/access policy, and security reviewed before launch |

Phases may be split into smaller approved tasks. Do not create empty canonical apps ahead of their phase. The sequence can change only through a documented reason and owner approval.

## Verification approach

Use Django checks and focused automated tests for application behavior. Verify public/draft access, authorization boundaries, exam timing and scoring, retries, and database constraints. Before deployment, test backup restoration rather than relying only on backup job success. Test with representative mobile viewport and slower network conditions. Establish performance targets and representative load scenarios before interpreting a load test; do not claim capacity from the monthly budget alone.

## Change and naming control

The canonical names are in `ARCHITECTURE.md` and `PROJECT_AI_RULES.md`. Before adding a module or variable, inspect existing code and explain why the current module or name cannot support the requirement. New names must be specific, documented, and approved with the relevant phase; preserve established public interfaces and data names. Do not introduce dependencies or infrastructure preemptively.
