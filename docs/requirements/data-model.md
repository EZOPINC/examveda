# Preliminary Data Model

**Status:** Phase 0 exam model remains conceptual. The Phase 2 content model and URL scheme are approved and implemented; migration `content.0001_initial` was reviewed and applied to the local PostgreSQL database.

## Relationship outline

```text
ExamCategory 1 ─── * ExamStage
ExamCategory/ExamStage 1 ─── * ResourceMetadata
Subject 1 ─── * Topic
ContentPage 1 ─── 0..1 ResourceMetadata 1 ─── * ResourceFile
Topic 1 ─── * ResourceMetadata

User 1 ─── * TestAttempt * ─── 1 MockTest (or immutable TestVersion)
                         |
                         └── 1 * AttemptResponse * ─── 1 Question (or question snapshot)

Subject/Topic 1 ─── * Question
MockTest 1 ─── * TestQuestion * ─── 1 Question

User 1 ─── * Entitlement (future)
User 1 ─── * PaymentTransaction (future)
LearningResource/Question/MockTest ─── * File reference (as required)
```

This is a logical relationship sketch. The approved Phase 2 content entities are scoped below; exam and future-payment entities remain conceptual and must not be created in this phase. The foundation uses Django's built-in user model; revisit only if confirmed account requirements justify a custom model, and do so before account features are built. Prefer an explicit through model for ordered test questions where ordering or per-test marks are needed.

## Approved Phase 2 content entities

**Implementation note:** The approved seven entities are implemented in `content.models` with the fields below and implementation-level details in migrations. Cross-table taxonomy checks run in model validation and Django admin forms; database constraints cover scoped slug uniqueness. PDF files use `MEDIA_ROOT` and are not served directly by a media URL.

| Entity | Candidate fields / relationships | Integrity and lifecycle notes |
| --- | --- | --- |
| ExamCategory | Name, unique slug, description, active/publication state, display order | Represents an exam family such as WBCS. Only categories with published content appear publicly. |
| ExamStage | ExamCategory relation, name, slug, display order | Slug is unique within its category; a resource's stage must belong to its category. |
| Subject | Name, unique slug, description, active state | Stable subject taxonomy shared by content now and questions later. |
| Topic | Subject relation, optional parent topic, name, slug, display order | Slug uniqueness is scoped to its subject; validate parent topic belongs to the same subject and reject cycles. |
| ContentPage | Title, globally unique slug, summary/body, language, publication state, `published_at`, SEO title/description, audit timestamps and staff authors | Drafts are invisible publicly. Publication requires valid content and a publication timestamp. Staff preview checks staff permission server-side. |
| ResourceMetadata | One-to-one ContentPage relation, ExamCategory, optional ExamStage, optional year, resource type, optional Subject/Topic | Stores exam and learning-resource classification without duplicating page body or publication state. Validate stage/category and topic/subject consistency. |
| ResourceFile | ResourceMetadata relation, uploaded file/storage key, original filename, content type, size, visibility (`public` or `restricted`), display order | Files are not served by a direct `MEDIA_URL`. Public delivery requires a published page and public visibility. Restricted files stay outside public web roots and have no public endpoint in this phase. |

Use UTF-8 text fields for Bengali and English; language is explicit metadata. `ContentPage` is the canonical body and publication record, while `ResourceMetadata` is optional classification for resource pages. File metadata is separate so pages can have zero or multiple documents. Avoid a rich-text or translation dependency until an editorial requirement justifies one.

Create database indexes for common public listings and filters (publication state/time, category/stage/year/type, and subject/topic) only after defining the corresponding query shape. Slug fields and scoped uniqueness constraints provide the lookup indexes where appropriate. Validate year bounds, language values, metadata relationships, file type/size, and publication requirements on the server; use database constraints for single-table invariants and model/form validation for cross-table relationships.

## Approved Phase 2 public URL scheme

- `/free-resources/`
- `/free-resources/<exam>/`
- `/free-resources/<exam>/<stage>/`
- `/free-resources/<exam>/<stage>/<year>/`
- `/free-resources/<exam>/<stage>/<year>/<resource-type>/`
- `/free-resources/<exam>/<stage>/<year>/<resource-type>/<resource-slug>/`
- `/free-resources/subjects/<subject>/`
- `/free-resources/subjects/<subject>/topics/<topic>/`
- `/free-resources/pages/<page-slug>/`

For example, `/free-resources/wbcs/prelims/2024/solutions/` is a public solution archive; adding a resource slug addresses one solution. This preserves the suggested archive URL while giving each resource a stable canonical URL. The route definitions, names, and reversal behavior must be covered by tests before release.

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
