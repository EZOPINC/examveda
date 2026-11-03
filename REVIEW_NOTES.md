# Documentation reconciliation — review notes

**Scope:** 15 uploaded Markdown files reviewed. This package revises 8 files, preserves `TROUBLESHOOTING.md` and Decisions 0001–0007 unchanged, and adds these notes. It does not inspect the Django repository or execute application tests.

## Conflicts resolved

1. The appended `ARCHITECTURE.md` target app names contradicted the existing implemented `content` and `exam_engine` app ownership. New app names are no longer treated as approved.
2. `ADR-001` called random-only tests approved, while Decision 0004 approved ordered authored tests. Random assembly is now proposed, not implemented.
3. `ADR-001` required version/snapshot history, while Decision 0004 chose graph immutability. Existing policy remains authoritative pending evidence and amendment.
4. The appended README implied a new implementation baseline despite existing multilingual mock tests, blog, social and study materials. The README now labels future extensions explicitly.
5. Duplicated AGENTS and global rules are consolidated while preserving the original operational rules.

## Important gaps before Codex writes code

- Actual models, migrations, and data were not supplied, so exact schema changes cannot be approved from these documents alone.
- The original requirement documents and `deploy/README.md` were referenced but not uploaded; review them before authorizing changes to schemas, URLs, or deployment.
- `DEVELOPMENT_ROADMAP.md` still has an older 'Current task' description. It is explicitly labeled historical in the new extension section; confirm the live task and status in Git before updating it further.
- The original Decision 0007 reports SQLite tests due to its historical execution environment; later changelog documents PostgreSQL-only development. Do not rewrite historical evidence retroactively.

## Suggested Codex first task

Read `AGENTS.md`, `PROJECT_AI_RULES.md`, `ARCHITECTURE.md`, `DEVELOPMENT_ROADMAP.md`, `ADR-001-modular-exam-platform.md`, Decisions 0003/0004/0007, and the actual Django models/migrations. Audit only; report exact reuse, gaps, and conflicting requirements. Do not edit code or apply migrations. Wait for owner approval.
