# ADR-001: Modular learning workflows and centralized Question Bank — proposal

**Status:** Proposed / owner review required; not an implementation authorization  
**Scope:** Future structured solved papers, reusable question metadata, randomized mock tests, and Practice.

## Context and existing constraints

The platform already implements a modular Django monolith. `content` owns taxonomy, study materials, PDFs and blog content (Decision 0003 and Decision 0006). `exam_engine` owns canonical questions, options, authored ordered tests, attempts, server-side scoring, and English/Hindi/Bengali exam translations (Decisions 0004 and 0007). Accounts and access control are implemented under Decision 0005. The new workflow must extend these foundations rather than replace them by default.

## Proposed decisions for review

1. **Question Bank as a capability:** Reuse `exam_engine.Question`, `QuestionOption`, and existing translation records as the canonical question/answer identities. Audit the schema before proposing metadata for difficulty, multiple exam categories, provenance, review, and import history. Do not create a parallel `question_bank` app or copy answer keys.
2. **Structured previous-year solutions:** Preserve existing `content` resource pages, PDF metadata and public URLs. Evaluate a minimal relationship for ordered question appearances in exam/year/subject/paper sessions. A PDF alone does not establish verified extracted questions or answers.
3. **Random mock-test assembly:** Propose server-side selection once per attempt, persisted selection/order and scoring policy. This conflicts with the currently approved ordered authored-test graph and requires an amendment to Decision 0004, including history, concurrency, insufficient-question and translation-completeness behavior. A target of 50 questions is a proposal, not a current default.
4. **Historical integrity:** Retain the existing immutable-after-first-attempt graph until an approved design demonstrates why a new snapshot/version approach is necessary.
5. **Practice:** Defer implementation and quota/paid policy until separately approved; no placeholder app is required.
6. **Question import:** Defer PDF/image parsing, OCR, JSON review, correction, and publish workflow to its own design and security review. No unreviewed extraction writes directly to canonical questions.

## Non-decisions

This proposal does **not** approve new `exams`, `question_bank`, `previous_year`, `mock_tests`, or `practice` Django apps; model relocation; destructive migrations; a new answer key; Hindi translations for free PDFs; payment/entitlement records; or production deployment.

## Required approval sequence

1. Audit actual Django models, migrations, routes, constraints, test coverage and sample data.
2. Draft a minimal proposed schema and ownership map, including exact existing models reused.
3. Identify amendments needed to Decisions 0003, 0004 and/or 0007 and present compatibility and data migration/rollback risks.
4. Obtain owner approval for each changed policy and phase before coding.
5. Implement one bounded phase at a time with PostgreSQL tests and manual verification.

## Open decisions

- Are previous-year solved questions independently verified, and how are paper/year/session/source identities represented?
- Which metadata are missing from existing questions and taxonomy, and which require many-to-many relations?
- Will random tests replace authored tests, coexist with them, or use a separately defined template?
- What is the per-attempt frozen selection and marking representation without corrupting historical attempts?
- Which questions and translated variants are eligible for random selection?
- What quotas and entitlements, if any, will Practice eventually require?

## Precedence

Approved Decisions 0001–0007 and the current implemented code remain authoritative. This proposal supersedes none of them until the owner explicitly approves a revised decision and migration plan.
