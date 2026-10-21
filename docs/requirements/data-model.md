# Preliminary Data Model

**Status:** Phase 2 content and Phase 3 exam models are implemented. Phase 4 preserves Django's built-in user model and adds no database entities; Phase 5A demo materials also reuse existing entities without a migration.

## Relationship outline

```text
ExamCategory 1 ─── * ExamStage
ExamCategory/ExamStage 1 ─── * ResourceMetadata
Subject 1 ─── * Topic
ContentPage 1 ─── 0..1 ResourceMetadata 1 ─── * ResourceFile
Topic 1 ─── * ResourceMetadata

Subject/Topic 1 ─── * Question 1 ─── * QuestionOption
MockTest 1 ─── * MockTestQuestion * ─── 1 Question
User 1 ─── * TestAttempt 1 ─── * AttemptResponse * ─── 1 MockTestQuestion
AttemptResponse 0..1 ─── 1 QuestionOption

User 1 ─── * Entitlement (future)
User 1 ─── * PaymentTransaction (future)
LearningResource/Question/MockTest ─── * File reference (as required)
```

This is a logical relationship sketch. The exam entities are scoped below. The foundation uses Django's built-in user model; account registration/profile work remains in the accounts phase. `MockTestQuestion` is the ordered through model and owns per-test marks. The approved immutability rule after a first attempt preserves historical meaning without version/snapshot tables.

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
- `/free-resources/<exam>/<subject>/` — exam-scoped subject archive for the study-material navigation. This shares the existing two-slug route shape with the stage archive; the view preserves a matching stage first and falls back to a subject within that exam.
- `/free-resources/<exam>/<subject>/<paper-slug>/` — published previous-year paper detail page using existing `ContentPage` and `ResourceMetadata` records.

For example, `/free-resources/wbcs/prelims/2024/solutions/` is a public solution archive; adding a resource slug addresses one solution. This preserves the suggested archive URL while giving each resource a stable canonical URL. The route definitions, names, and reversal behavior must be covered by tests before release.

The local demo study-material set adds no model or migration. Exam-to-subject membership is represented by the existing `ResourceMetadata.category` and `.subject` relationship; page body, publication state, title, slug, and year remain on `ContentPage` and `ResourceMetadata`. Demo identity uses a reserved `demo-` slug prefix plus clear editorial text in the title, summary, and body rather than an additional schema flag; the public detail banner recognizes that prefix.

## Approved Phase 3 exam entities

| Entity | Responsibilities and invariants |
| --- | --- |
| Question | Prompt, explanation, language, subject/topic, publication state. Phase 3 question type is single-choice. A published question has at least two options and exactly one correct option. |
| QuestionOption | One option's text, correctness flag, and display order. Correctness is omitted from active exam responses. |
| MockTest | Public title/slug/description, duration, availability interval, publication state, author. Only published, available tests can start. |
| MockTestQuestion | Ordered test/question join, positive marks, non-negative negative marks no greater than positive marks. Test and question must be published; order and test/question pair are unique. |
| TestAttempt | Student, test, state (`in_progress`, `submitted`, `expired`), server timestamps, score and correct/incorrect/unanswered totals. One active attempt per student/test. |
| AttemptResponse | One row per attempt/test-question with nullable selected option and server update time. Selected option must belong to the joined question. |

There is no separate result table: final score/counts live atomically on `TestAttempt`. There are no version tables: the test/question graph becomes immutable after its first attempt; editors create new records for revisions. `finalized_at` records the terminal transition for both submission and expiry; `submitted_at` is set only for student submission.

## Future entities and responsibilities

The Phase 3 entities above are implemented and must not be recreated under alternate names. `Subject` and `Topic` are owned by `content`; `Question`, `QuestionOption`, `MockTest`, `MockTestQuestion`, `TestAttempt`, and `AttemptResponse` are owned by `exam_engine`. Future phases may add only genuinely new entities after requirements and decisions are approved.

| Entity | Candidate fields / relationships | Integrity and lifecycle notes |
| --- | --- | --- |
| User/profile extension | Existing Django user identity; no separate profile required by current approved behavior | Preserve the established built-in user model; any later identity change requires a documented data migration and explicit approval. |
| Entitlement (future; not implemented) | User, entitlement code/scope, validity interval, verified source transaction, status/revocation timestamp | Server-authoritative access; auditable grants, expiry and revocation. Create only with approved paid-access requirements and migration review. |
| PaymentTransaction (future) | User, provider reference, amount/currency, status, timestamps, idempotency reference | Never store card credentials; reconcile provider state and duplicate callbacks. |
| Other future entity | Define only when an approved feature requires it | Avoid duplicating existing content and exam entities; document the decision and migration impact first. |

Field lists are indicative, not a mandate to add every field. Add only fields required by approved behavior. Prefer Django-managed primary keys and conventional table/constraint names. Add named constraints and indexes only where they enforce an invariant or support measured query patterns.

## Decision 0004 implementation notes

### Test and question history

Test/question records are immutable after an attempt starts; use new records for revisions. This avoids extra version tables while preserving historical result meaning. Revisit if editorial workflows show that copied records are error-prone.

### Response representation

Only single-choice is supported in this phase. A student may revise or clear an answer until submission or the deadline. Store a nullable option foreign key, not arbitrary answer JSON.

### Score persistence

Store score, correct, incorrect, and unanswered counts on `TestAttempt`, calculated from the frozen test graph and saved responses in the same finalization transaction. There is no separate result entity because the relationship is one result per attempt.

### Constraints and transactions

Use database uniqueness/check constraints for invariants such as one response per attempt and question and unique question ordering within a test where supported. Use transactions for start, submission, scoring, and entitlement grants that involve multiple writes. Avoid relying on form validation alone under concurrency.

## Naming and migrations

Canonical app names are `accounts`, `content`, `exam_engine`, `access_control`, `payments`, and `file_delivery`; their creation is feature-driven. Preserve established model, field, URL, and configuration names after adoption. Any later rename or schema restructure requires a data-preserving migration plan, impact review, backup considerations, and approval before production use.

Phase 4 adds no model or migration: `accounts` uses Django's built-in user record, and `access_control` currently contains a policy service only. Do not create an `Entitlement` or payment transaction model until the separate paid-access phase is approved.
