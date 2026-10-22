# Decision 0007: Multilingual mock exams

**Status:** Approved and implemented for review on 2026-10-22. Production rollout and data updates remain separate operator actions.

## Context

The application needs an English, Hindi, and Bengali interface and mock exams. A logical question must retain one scoring key across languages, and students must be able to change display language during an attempt without changing their timer, saved answers, or attempt identity. Free educational content and previous-year question papers keep their existing English/Bengali editorial workflow; this decision does not add Hindi material or transform PDF uploads.

## Decision

- Keep all exam behavior within the existing `exam_engine` models, services, views, forms, admin, templates, and static files. Do not create another Django application or a generic translation framework.
- Keep source text on `Question`, `QuestionOption`, and `MockTest`. Add `QuestionTranslation` for prompt/explanation and publication state, `QuestionOptionTranslation` for text linked to an existing stable `QuestionOption`, and `MockTestTranslation` for translated title/description/instructions and publication state.
- Keep `QuestionOption.is_correct` as the only answer key. No translation row stores correctness. The same option IDs are used for selection and scoring in every language.
- Widen `Question.language` to ten characters and add `hi` to the existing `en`/`bn` source-language choices. Keep the three UI languages in Django `LANGUAGES` and localized message catalogs under `locale/`.
- Add nullable `MockTest.language`, source `MockTest.instructions`, and nullable `TestAttempt.language_code`. New attempts require an explicit available language. Existing test/attempt rows are not backfilled or inferred; staff review is needed before existing tests can start under this policy. Existing attempts with a null locale retain their source-question review path.
- Require a published test variant and published source questions. For a translated variant, require a non-empty prompt, a non-empty label for every stable option, and a translated explanation when the source question has one. Require translated metadata corresponding to any non-empty source description/instructions. Never mix languages to fill a missing field.
- Reuse test/question graph immutability after the first attempt. Translation text cannot be added, edited, or deleted once any attempt references the graph. Staff may close a locale to new starts/switches; existing attempts continue to render their stored language.
- Store the selected language on the attempt. Language switching updates this field only. It does not create an attempt, save or reinterpret an answer, reset timestamps, or alter score calculation.
- Use Django `LocaleMiddleware`, the built-in `set_language` view, `{% trans %}`/`{% blocktrans %}`, and compiled UTF-8 `.mo` catalogs. Use local font-family fallbacks for Devanagari and Bengali. No new runtime package, external font request, or frontend framework is added.
- Preserve previous-year PDF upload and delivery as a separate workflow owned by `content`; do not turn PDFs into mock questions.

## Why this fits

The existing exam graph already provides stable option rows and one trusted scoring flag. Translation rows attached to those identities prevent language variants from duplicating tests or answer keys. The nullable legacy fields let the migration preserve existing records without making an unsupported claim about their authored language. The service completeness check remains authoritative for both public language listings and attempt start/switch requests, while admin indicators reuse that check.

## Migration and compatibility

Migration `exam_engine.0002_mocktest_instructions_mocktest_language_and_more` depends only on `exam_engine.0001_initial`. It adds three tables, two nullable fields, source instructions, widens the question language column, and adds uniqueness constraints. It contains no data migration, deletion, or default that assigns a language to existing tests/attempts. Existing `en` and `bn` values remain valid. Existing attempt ownership, responses, timestamps, scores, and correctness values are untouched.

Before enabling old tests after deployment, an administrator must inspect each test and its questions and determine whether its graph has any attempt history. A test with no attempts may be assigned a source language only after the actual authored language is verified, then receive complete translations and a readiness review. A test/question graph with attempts is immutable: retain it for history and do not assign a guessed language, edit its wording, or add translations to its questions. If that content is needed in the new public workflow, author a new question/test graph from independently verified source material. Back up the database and apply the additive migration through the existing deployment process after review. The migration was generated and checked against model state locally; PostgreSQL application and rollback rehearsal remain deployment verification tasks.

## Administrator workflow

1. Create/edit a source question, choose its language, and manage the source options and single shared correct answer in the existing Question admin.
2. Open **Manage question translations**. Add one locale row, translate the prompt and any source explanation, then use the option inline to label every existing option. The admin completeness indicator identifies missing text; a locale cannot be published through the inline formset until every option is present.
3. Review the escaped localized question preview (`lang` attribute is set); it intentionally does not mark the correct option in the preview.
4. Create a MockTest, set its source language and shared duration/availability, and compose it from the existing questions. Add translated metadata in the test translation inline. The admin **Ready languages** column shows only variants that pass the same service check used by public pages and start requests.
5. Publish the test and any desired complete variants. The language only appears publicly after its entire question set is ready. To stop future use, unpublish the test or translation; existing attempts keep their stored locale.

## Student flow

The public test detail page offers currently complete languages before the start POST. The server validates that choice and stores it on the created attempt. The attempt page restores that locale on refresh. If another complete, currently published variant exists, a language form waits for pending answer saves and posts the locale change. The attempt row lock and unchanged response IDs/timestamps preserve the active exam state; the server still controls the original deadline and scoring.

## Verification and limits

Automated tests cover availability/publication completeness, missing prompts/options/explanations/metadata, shared correctness, required start locale, attempt language persistence/switching, unchanged saved answer and server times, UI catalog rendering, and active answer-key hiding. Django checks and tests currently use a temporary in-memory SQLite database because no PostgreSQL connection is configured in the development process. Run PostgreSQL migration, Unicode round-trip, and admin workflow verification before deployment. A visual check with real Hindi/Bengali fonts at mobile widths remains a manual task.

## Revisit only with evidence

Consider a separate translation management abstraction only if the same workflows expand beyond the current question/test fields or measured duplication warrants it. Consider version snapshots only if editors demonstrate that frozen graph revisions are error-prone. Consider per-language question order/scoring only if product requirements explicitly require test variants with different exam content; it would need a new scoring and attempt-history design.
