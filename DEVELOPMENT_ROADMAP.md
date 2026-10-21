# Development Roadmap

**Status:** Phases 2, 3, and 4 are owner-approved (Phase 3 and 4 approval explicitly confirmed on 2026-10-20). Phase 5 code review is complete with operational gates open. Phase 6 is authorized; deployment configuration and runbook preparation are underway. No OCI resources have been provisioned.

**Current task:** Phase 6 deployment configuration and operations documentation. The Phase 5 report's restore, load, proxy, monitoring, and rate-limit gates remain open and are not resolved by local deployment preparation.

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
| 2. Free content | `content` models and public pages, publication workflow, language-aware content, stable public URLs | Approved complete on 2026-10-15; PostgreSQL checks and tests pass, and published/draft workflow is covered through automated HTTP/admin-path tests |
| 3. Exam engine | `exam_engine` question/test authoring, attempt lifecycle, server-side timing, autosave, submission, score, permitted review | Owner-approved 2026-10-20 after implementation and PostgreSQL-backed verification |
| 4. Accounts and access | Registration/login, profile needs, history, shared policies where needed | Owner-approved 2026-10-20 after student/admin separation, ownership, and fail-closed entitlement verification |
| 5. Security and quality | Cross-feature security review, accessibility, mobile/slow-network checks, performance baseline, backup/restore rehearsal, monitoring design | Findings and accepted risks documented; tests and measured performance evidence reviewed; operational validation requires an authorized isolated environment |
| 6. Deployment | OCI Linux deployment, Nginx, Gunicorn, PostgreSQL, HTTPS, secrets, backup/restore, monitoring, rollback | Deployment and restore runbooks exercised; production settings and readiness evidence approved |
| Future paid access | Membership and paid tests, `payments`, provider integration and relevant access rules | Provider callbacks, idempotency, reconciliation, refund/access policy, and security reviewed before launch |

Phases may be split into smaller approved tasks. Do not create empty canonical apps ahead of their phase. The sequence can change only through a documented reason and owner approval.

## Verification approach

Use Django checks and focused automated tests for application behavior. Verify public/draft access, authorization boundaries, exam timing and scoring, retries, and database constraints. Before deployment, test backup restoration rather than relying only on backup job success. Test with representative mobile viewport and slower network conditions. Establish performance targets and representative load scenarios before interpreting a load test; do not claim capacity from the monthly budget alone.

## Change and naming control

The canonical names are in `ARCHITECTURE.md` and `PROJECT_AI_RULES.md`. Before adding a module or variable, inspect existing code and explain why the current module or name cannot support the requirement. New names must be specific, documented, and approved with the relevant phase; preserve established public interfaces and data names. Do not introduce dependencies or infrastructure preemptively.
