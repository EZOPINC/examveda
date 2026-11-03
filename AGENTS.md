# WBPSC Mock Exam Platform — Codex Project Instructions

Before making changes, read `PROJECT_AI_RULES.md` and any relevant project documentation.

## Project

Build a secure, maintainable WBPSC examination preparation platform with free learning content, mock tests, student accounts, and future paid memberships.

## Approved technology baseline

- Python and Django
- PostgreSQL
- Django templates, HTML, CSS, and vanilla JavaScript
- Nginx and Gunicorn
- Oracle Cloud Infrastructure
- Git

## Mandatory rules

1. Follow `PROJECT_AI_RULES.md` for architecture, naming, documentation, security, testing, and troubleshooting.
2. Preserve established module names, function names, model names, fields, URLs, and configuration keys.
3. Inspect the repository and Git status before modifying files.
4. Work only on the explicitly approved phase or task.
5. Explain substantial changes before implementing them.
6. Do not rename, replace, or refactor unrelated code without approval.
7. Add maintenance-oriented docstrings and comments to new modules and significant code sections.
8. Never claim tests passed unless they were actually run.
9. Never perform destructive database operations without explicit approval and a verified backup.
10. Never expose credentials, secrets, or sensitive data.
11. Run relevant tests and inspect the diff after implementation.
12. Update the relevant documentation, module registry, and changelog.
13. Stop at the end of each phase and wait for approval.

## Required completion report

Report files changed, key decisions, migrations, tests actually run, verification steps, unresolved issues, and the recommended next task.

## Codex Development Efficiency Rules

### Scope and exploration
- Work on one clearly defined task at a time.
- Read repository instructions once per task, then inspect only files relevant to the requested module and its direct dependencies.
- Do not scan the entire repository or read unrelated documentation unless necessary.
- Check Git status before editing and preserve existing uncommitted changes.
- Prefer minimal, localized changes over refactoring or architectural redesign.
- Do not modify unrelated modules, templates, configuration, or dependencies without explaining why they are necessary.

### Task classification
Classify each request as SMALL, MODULE, or CRITICAL.

**SMALL:** CSS, content, labels, localized UI fixes, and simple template changes.

**MODULE:** Changes to one feature's views, forms, models, APIs, or workflows.

**CRITICAL:** Database migrations, authentication, permissions, exam scoring, attempt timing, payment logic, data integrity, or shared infrastructure.

### Testing policy
- SMALL: Run the narrowest applicable check or targeted test. For purely visual changes, provide manual verification steps when automated coverage is not applicable.
- MODULE: Run relevant module tests and directly affected integration tests.
- CRITICAL: Run focused tests plus broader integration or full-suite tests as appropriate to the risk.
- Do not automatically run the full test suite for SMALL changes.
- Do not run unrelated load tests, builds, or deployment checks.
- If tests cannot run, report why. Never claim an unexecuted test passed.
- Expand testing only when failures or dependencies justify it.

### Token and output efficiency
- Keep analysis, tool output, and final summaries concise.
- Avoid dumping entire files, test logs, or Git diffs when a short summary is sufficient.
- Do not repeatedly read files already inspected during the same task unless they changed.
- Avoid generating unnecessary documentation or extensive plans for straightforward fixes.
- Do not add new tests for cosmetic-only changes unless they protect meaningful behavior.

### Completion
Report only:
1. Files changed and what changed.
2. Checks/tests run and results.
3. Risks, limitations, or manual steps.

Do not commit, push, deploy, restart production services, or run destructive database operations without explicit approval.

## Architecture-change gate

Before work involving the Question Bank, previous-year solved papers, random mock tests, or Practice, read the relevant approved ADRs and the proposal in `ADR-001-modular-exam-platform.md`. Identify whether the task is a current implementation change or a proposed architectural change. Preserve `content` and `exam_engine` ownership and existing migrations. For any conflict with Decisions 0003, 0004, or 0007, produce a design/compatibility proposal and stop for approval; do not implement a speculative new Django app.

Use the existing SMALL / MODULE / CRITICAL classification and testing rules above; avoid duplicate instructions. No commit, push, deployment, production restart, or destructive operation without explicit approval.
