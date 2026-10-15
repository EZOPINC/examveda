# Preliminary Data Model

**Status:** Conceptual Phase 0 model, not a migration specification. Names are stable planning terms; implementation details require feature approval.

## Relationship outline

```text
User 1 ─── * TestAttempt * ─── 1 MockTest (or immutable TestVersion)
                         |
                         └── 1 * AttemptResponse * ─── 1 Question (or question snapshot)

Subject 1 ─── * Topic 1 ─── * LearningResource
Subject/Topic 1 ─── * Question
MockTest 1 ─── * TestQuestion * ─── 1 Question

User 1 ─── * Entitlement (future)
User 1 ─── * PaymentTransaction (future)
LearningResource/Question/MockTest ─── * File reference (as required)
```

This is a logical relationship sketch, not an instruction to create all models immediately. The foundation uses Django's built-in user model; revisit only if confirmed account requirements justify a custom model, and do so before account features are built. Prefer an explicit through model for ordered test questions where ordering or per-test marks are needed.

## Candidate entities and responsibilities

| Entity | Candidate fields / relationships | Integrity and lifecycle notes |
| --- | --- | --- |
| User | Django identity and authentication fields; optional profile relation | Decide custom user model before migrations. Keep profile data minimal. |
| Subject | Name, slug, publication/active state as needed | Avoid duplicate taxonomy representations across content and exams. |
| Topic | Subject relation, name, slug, optional parent topic | If hierarchy is required, prevent cycles and keep queries bounded. |
| LearningResource | Title, slug, language, content/body or file reference, topics, publication timestamps/state, metadata | Public only when published and explicitly public; slugs must be stable. |
| Question | Prompt, language, type, explanation, publication state, subject/topic relation | Question changes must not mutate historical attempt meaning. |
| QuestionOption | Question relation, option content, stable ordering | Correctness data is server-only until review is allowed. Enforce valid option/question combinations. |
| MockTest | Name, slug, description, availability, duration, scoring policy, review policy, access policy | Validate duration and policy values; public description is distinct from protected test data. |
| TestQuestion | Test/version relation, question or snapshot, position, optional marks | Unique ordering within the test; test membership defines which questions an attempt may answer. |
| TestAttempt | User, test/version, state, `started_at`, `expires_at`, `submitted_at`, result fields if stored | Ownership and lifecycle enforced in server operations and constraints where possible. Store timestamps in UTC. |
| AttemptResponse | Attempt, question/snapshot, selected option(s), save timestamps | At most one logical response per attempt-question; validate selected options belong to that question. |
| Entitlement (future) | User, entitlement type, validity interval, source/status | Server-authoritative access; auditable expiration/revocation. |
| PaymentTransaction (future) | User, provider reference, amount/currency, status, timestamps, idempotency reference | Never store card credentials; reconcile provider state and duplicate callbacks. |
| File reference | Storage key, visibility/classification, owning feature, metadata | Do not treat an unguessable key as authorization. Keep storage credentials private. |

Field lists are indicative, not a mandate to add every field. Add only fields required by approved behavior. Prefer Django-managed primary keys and conventional table/constraint names. Add named constraints and indexes only where they enforce an invariant or support measured query patterns.

## Decisions required before exam implementation

### Test and question history

Choose either immutable test/question versions or snapshots associated with attempts. The required outcome is that later editing does not change the questions, answer key, scoring rules, or interpretation of a historical result. Compare editorial complexity, storage, auditability, and query needs before selecting an implementation.

### Response representation

Confirm supported question types (single choice, multiple choice, other) and whether an answer can be revised until submission/expiry. Model selected options with relationships and constraints rather than trusting arbitrary client JSON unless a reviewed requirement justifies another representation.

### Score persistence

Decide which score components need to be retained for audit and history. Whether score is stored or derived, calculate it on the server from the attempt's effective test version and responses. If stored, write the result atomically at finalization and prevent later response edits.

### Constraints and transactions

Use database uniqueness/check constraints for invariants such as one response per attempt and question and unique question ordering within a test where supported. Use transactions for start, submission, scoring, and entitlement grants that involve multiple writes. Avoid relying on form validation alone under concurrency.

## Naming and migrations

Canonical app names are `accounts`, `content`, `exam_engine`, `access_control`, `payments`, and `file_delivery`; their creation is feature-driven. Preserve established model, field, URL, and configuration names after adoption. Any later rename or schema restructure requires a data-preserving migration plan, impact review, backup considerations, and approval before production use.
