# Preliminary Data Model

**Status:** Phase 2 content and Phase 3 exam models are implemented. The approved multilingual exam extension adds three translation entities and additive schema in `exam_engine.0002`. Phase 4 preserves Django's built-in user model. Phase 5A demo materials reuse existing entities; the blog extension adds `BlogCategory` and optional editorial fields on `ContentPage` in migration `content.0002`.

## Relationship outline

```text
ExamCategory 1 ─── * ExamStage
ExamCategory/ExamStage 1 ─── * ResourceMetadata
Subject 1 ─── * Topic
ContentPage 1 ─── 0..1 ResourceMetadata 1 ─── * ResourceFile
Topic 1 ─── * ResourceMetadata
BlogCategory 1 ─── * ContentPage (optional article classification)

Subject/Topic 1 ─── * Question 1 ─── * QuestionOption
MockTest 1 ─── * MockTestQuestion * ─── 1 Question
User 1 ─── * TestAttempt 1 ─── * AttemptResponse * ─── 1 MockTestQuestion
AttemptResponse 0..1 ─── 1 QuestionOption
Question 1 ─── * QuestionTranslation 1 ─── * QuestionOptionTranslation * ─── 1 QuestionOption
MockTest 1 ─── * MockTestTranslation

User 1 ─── * Entitlement (future)
User 1 ─── * PaymentTransaction (future)
LearningResource/Question/MockTest ─── * File reference (as required)
```

This is a logical relationship sketch. The exam entities are scoped below. The foundation uses Django's built-in user model; account registration/profile work remains in the accounts phase. `MockTestQuestion` is the ordered through model and owns per-test marks. `QuestionOptionTranslation` links localized labels to stable shared option rows; it does not copy correctness. `TestAttempt.language_code` records the presentation language. The approved immutability rule after a first attempt preserves historical meaning without version/snapshot tables.

## Approved Phase 2 content entities

**Implementation note:** The approved seven entities are implemented in `content.models` with the fields below and implementation-level details in migrations. Cross-table taxonomy checks run in model validation and Django admin forms; database constraints cover scoped slug uniqueness. PDF files use `MEDIA_ROOT` and are not served directly by a media URL.

| Entity | Candidate fields / relationships | Integrity and lifecycle notes |
| --- | --- | --- |
| ExamCategory | Name, unique slug, description, active/publication state, display order | Represents an exam family such as WBCS. Only categories with published content appear publicly. |
| ExamStage | ExamCategory relation, name, slug, display order | Slug is unique within its category; a resource's stage must belong to its category. |
| Subject | Name, unique slug, description, active state | Stable subject taxonomy shared by content now and questions later. |
| Topic | Subject relation, optional parent topic, name, slug, display order | Slug uniqueness is scoped to its subject; validate parent topic belongs to the same subject and reject cycles. |
| ContentPage | Title, globally unique slug, summary/body, language, publication state, `published_at`, SEO title/description, audit timestamps and staff authors; optional `BlogCategory`, byline, featured image and image alt text | One canonical editorial body serves study materials and blog articles. Drafts are invisible publicly. Blog images are signature/size checked, use alt text when published, and are streamed only through publication-checked routes. |
| BlogCategory | Name, unique slug, optional description | Separate editorial taxonomy; public categories appear only while they contain a currently published article. Referenced categories cannot be deleted while articles use them. |
| ResourceMetadata | One-to-one ContentPage relation, ExamCategory, optional ExamStage, optional year, resource type, optional Subject/Topic | Stores exam and learning-resource classification without duplicating page body or publication state. Validate stage/category and topic/subject consistency. |
| ResourceFile | ResourceMetadata relation, uploaded file/storage key, original filename, content type, size, visibility (`public` or `restricted`), display order | Files are not served by a direct `MEDIA_URL`. Public delivery requires a published page and public visibility. Restricted files stay outside public web roots and have no public endpoint in this phase. |

Use UTF-8 text fields for Bengali and English free-content records; language is explicit metadata. Hindi is not added to the free previous-year-paper workflow. The shared application UI and mock-exam content support English, Hindi, and Bengali. `ContentPage` is the canonical body and publication record, while `ResourceMetadata` is optional classification for resource pages. File metadata is separate so pages can have zero or multiple documents. Avoid a rich-text or translation dependency until an editorial requirement justifies one.

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

### Blog extension (`content.0002`)

The blog reuses `ContentPage` for body, slug, language, publication state/time, summary, SEO metadata, and audit fields. Its optional `blog_category`, `author_name`, `featured_image`, and `featured_image_alt` fields add the article presentation details. `BlogCategory` is separate because exam `Topic` belongs to a `Subject` and is not a general editorial category. The migration is additive and preserves existing rows; no article records are seeded automatically. Category/archive/article paths are `/blog/`, `/blog/category/<category-slug>/`, and `/blog/<article-slug>/`. Only published articles and categories with published articles enter `/sitemap.xml`.

## Approved Phase 3 exam entities

| Entity | Responsibilities and invariants |
| --- | --- |
| Question | Prompt, explanation, language, subject/topic, publication state. Phase 3 question type is single-choice. A published question has at least two options and exactly one correct option. |
| QuestionOption | One option's text, correctness flag, and display order. Correctness is omitted from active exam responses. |
| MockTest | Public title/slug/description, duration, availability interval, publication state, author. Only published, available tests can start. |
| MockTestQuestion | Ordered test/question join, positive marks, non-negative negative marks no greater than positive marks. Test and question must be published; order and test/question pair are unique. |
| TestAttempt | Student, test, state (`in_progress`, `submitted`, `expired`), server timestamps, score and correct/incorrect/unanswered totals. One active attempt per student/test. |
| AttemptResponse | One row per attempt/test-question with nullable selected option and server update time. Selected option must belong to the joined question. |

### Approved multilingual mock-exam extension

The exam UI and mock-test content support `en`, `hi`, and `bn` from the initial release. Django's `LocaleMiddleware`, standard language-selection endpoint, message catalogs, and template translation tags localize interface text. Free previous-year-paper content remains in its existing English/Bengali workflow; no Hindi content field or PDF transformation is added.

| Entity/field | Shared or translated data | Integrity and migration notes |
| --- | --- | --- |
| `Question.language` | Source language of the logical question; source prompt, explanation, publication flag, subject/topic, and options remain on `Question`/`QuestionOption` | Widen `max_length` from 2 to 10 and add Hindi to choices. Existing values are preserved. |
| `QuestionTranslation` | One row per question/locale with translated prompt, explanation, and publication state | Unique by question and locale. Source-language duplication is rejected. Published locale must have all option labels and required explanation text. |
| `QuestionOptionTranslation` | Localized label for one existing `QuestionOption` identity | Unique by translation/option; option must belong to the same logical question. `QuestionOption.is_correct` remains the only answer key. |
| `MockTest.language` and `instructions` | Source language and source instructions stay on `MockTest`; duration, availability, slug, scoring composition and source description stay shared | New language is nullable for legacy tests. Existing rows are not guessed or bulk assigned; staff can assign a verified language before any attempt. Attempted graphs remain immutable and must be reauthored as new questions/tests if needed. |
| `MockTestTranslation` | Localized title, description, instructions, and locale publication state | Unique by test/locale. A language is available only when metadata and every contained question variant are published and complete. |
| `TestAttempt.language_code` | Selected locale for this attempt; answers, question identities, timing and score are shared | Nullable only to preserve old attempt history. All new starts require an explicit available locale. Language switching updates this field only. |

For a translated question, the prompt, every option label, and an explanation are required when the source question has an explanation. A language is never silently filled from another locale. Unpublished or incomplete variants are omitted from public availability and rejected by the start and switch services. Content wording remains immutable after an attempt starts; closing a locale can stop new selections while an existing attempt continues to render its recorded language. The additive migration does not seed translations, change existing attempt rows, or rewrite content.

There is no separate result table: final score/counts live atomically on `TestAttempt`. There are no version tables: the test/question graph becomes immutable after its first attempt; editors create new records for revisions. `finalized_at` records the terminal transition for both submission and expiry; `submitted_at` is set only for student submission.

## Future entities and responsibilities

The Phase 3 entities above are implemented and must not be recreated under alternate names. `Subject` and `Topic` are owned by `content`; `Question`, `QuestionOption`, `MockTest`, `MockTestQuestion`, `TestAttempt`, `AttemptResponse`, `QuestionTranslation`, `QuestionOptionTranslation`, and `MockTestTranslation` are owned by `exam_engine`. Future phases may add only genuinely new entities after requirements and decisions are approved.

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
