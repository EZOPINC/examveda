# Functional Requirements

**Status:** Phases 2–4 are owner-approved. Phase 5 review is in progress; Phase 5A adds local demo navigation validation without changing the product data model. Future product policies remain open until their phases.

The blog and social extension adds public editorial browsing using the existing `ContentPage` lifecycle. Blog categories, article detail pages, social-profile configuration, share controls, and public sitemap behavior are described below; no social feed or payment functionality is introduced.

## Roles and journeys

### Visitor and student

- A visitor can browse published free articles, notes, study materials, previous-year questions, solutions, and public test descriptions without an account.
- A visitor can register a student account at `/accounts/register/`, sign in, and sign out. Registration uses Django's built-in user model and cannot grant staff or administrator privileges.
- A signed-in student can view their own account, update their email, change their password, and view their own attempt history. A lost password is recovered through an administrator after identity verification until verified-email recovery is approved and configured.
- An authenticated student can start an available test, answer questions, save responses, resume an eligible attempt, submit, and view permitted results.
- A student can view only their own attempt history and details.
- A student can access protected materials only when the configured access rule grants it.
- A student can use core pages and exam controls on a mobile device and on a slower connection; the server remains authoritative if browser requests are delayed.

### Administrator and editor

- Authorized staff can create, edit, preview, publish, unpublish, and archive educational content.
- Authorized staff can create and maintain subjects, topics, questions, options, explanations, tests, ordering, duration, scoring, availability, and review policy.
- Staff and administrator privileges are granted only through Django admin or trusted operator commands. Public registration cannot assign staff status, groups, or permissions. Staff permissions continue to use Django's built-in model permissions; a custom interface needs a demonstrated requirement.
- Once an attempt exists, test identity/description/duration, ordered question composition, scoring values, question text, options, answer key, and explanations are immutable. Staff may unpublish a test or change its availability to stop new starts; existing attempts remain accessible until their deadline. Revisions use new question/test records; separate version and result entities are not required for the initial workflow.

## Free content and public URLs

- Public content has stable, lowercase, hyphenated slugs and can be linked directly. The Phase 2 content URL scheme is approved as follows:
  - `/free-resources/` — all published free materials.
  - `/free-resources/<exam>/` — an exam category such as WBCS.
  - `/free-resources/<exam>/<stage>/` — a stage such as prelims or mains within that category.
  - `/free-resources/<exam>/<stage>/<year>/` — a year archive.
  - `/free-resources/<exam>/<stage>/<year>/<resource-type>/` — a year archive filtered by type, including `solutions`.
  - `/free-resources/<exam>/<stage>/<year>/<resource-type>/<resource-slug>/` — one resource.
  - `/free-resources/subjects/<subject>/` — a subject listing.
  - `/free-resources/subjects/<subject>/topics/<topic>/` — a topic listing.
  - `/free-resources/pages/<page-slug>/` — an editorial content page.
- Resource type archive slugs are controlled values, not arbitrary user input. Route names are namespaced under `content`; internal links use Django URL reversal.
- `/mock-tests/` and `/mock-tests/<test-slug>/` are implemented by the exam engine; descriptions are public and private attempt URLs require authentication and ownership.
- Category, stage, year, resource type, subject, and topic pages list only published content. An empty or unknown filter returns a normal not-found response rather than revealing draft records.
- The local free-study-material navigation may browse exam categories to exam-scoped subjects and published previous-year question-paper pages. Illustrative demo pages must be visibly identified as non-authentic and unverified, and remain ordinary published `ContentPage`/`ResourceMetadata` records; they do not use the mock-exam engine.
- Content can be authored in Bengali or English. Language selection, search behavior, and whether individual resources can have parallel translations remain open decisions.
- Only published items intended for public access are visible to anonymous visitors. Preview and draft routes require staff authorization.
- Staff preview requires an authenticated staff account and is served through a protected application view; an unpublished page or its files are never exposed by a public detail or PDF route.
- Public content pages should include descriptive titles and metadata suitable for search indexing; private student data and attempts must not be indexed.
- Blog articles reuse `ContentPage` for body, slug, excerpt, language, publication and SEO fields; `BlogCategory` supplies editorial taxonomy, while optional byline and featured-image fields support article presentation. Draft and future-dated articles must 404 publicly, stay out of sitemap/schema output, and use protected staff preview for text and images.
- Public blog routes are `/blog/`, `/blog/category/<category-slug>/`, and `/blog/<article-slug>/`. Blog index/category/article pages provide breadcrumbs, canonical/title/description/Open Graph metadata and Article JSON-LD only on public article pages. The sitemap includes published articles and non-empty published categories.
- Footer social links are optional `SOCIAL_FACEBOOK_URL`, `SOCIAL_INSTAGRAM_URL`, `SOCIAL_TELEGRAM_URL`, and `SOCIAL_YOUTUBE_URL` environment values. Only HTTPS links with a host and no embedded credentials are rendered. External links use `noopener noreferrer`; no embedded social feed or third-party script is used. YouTube remains in the footer.
- Public blog articles and free study-material pages offer native share when supported and an accessible copy-link fallback. Controls rely on lightweight browser APIs and do not expose drafts or private student data.
- Public PDF resources may be displayed inline in a browser where supported. Browser display cannot prevent saving, printing, screenshots, or copying; do not promise copy protection.

## Questions, tests, attempts, and responses

- A question belongs to the appropriate subject/topic taxonomy and contains prompt content, answer options, explanation, language, and publication state. Phase 3 supports single-choice questions only. A published question must have at least two options and exactly one correct option.
- A test defines ordered published questions, duration, availability, and per-question marks and negative marks. Duration is 1–240 minutes; positive marks are required; negative marks range from zero through the question's positive marks.
- Every authenticated student may make unlimited attempts. Starting an available test resumes that student's existing unexpired attempt; after a terminal attempt, another start creates a new attempt.
- A response selects one option or clears the selection. It is unique per attempt/question and can be changed only while the attempt is in progress and before its server deadline.
- Correct responses earn the configured marks, incorrect responses lose the configured negative marks, and unanswered responses earn zero. There is no partial credit. Scores may be negative; the server records score and correct/incorrect/unanswered counts at finalization.
- Result scores/counts and answer key/explanation review become available immediately after student submission or expiry finalization. No result details or answer key are sent in the active exam response.

## Exam lifecycle

Proposed states: `in_progress`, `submitted`, and `expired`. A separate pre-start record is unnecessary unless a confirmed workflow requires it.

1. On start, the server checks authentication, availability, and question-set validity, resumes an owned active attempt when present, or records `started_at` and the server-computed `expires_at` for a new attempt. Attempts are unlimited.
2. The browser displays remaining time using server-provided timing data. It is not trusted to enforce duration.
3. Autosave verifies the authenticated owner, attempt state, expiry, question membership, and valid response data. Retries must not create duplicate responses.
4. Resume is allowed only for an owned, in-progress attempt before its deadline. An active attempt remains resumable if staff closes the test to new starts.
5. Submission verifies ownership and state, records a server timestamp, calculates and stores or reproducibly derives the result, and makes repeat submission requests safe.
6. At or after expiry, the server prevents further answer changes and finalizes the attempt as expired, scoring its saved responses.
7. Result review reveals scores, answer keys, and explanations immediately after submission or expiry finalization.

### Approved attempt lifecycle policies (Decision 0004)

1. Starting requires authentication, a published and available test, and a valid published question set. The server records `started_at` and `expires_at = started_at + duration`.
2. A student's in-progress attempt resumes until its deadline. The browser timer is only a display aid.
3. A save or submit at `now >= expires_at` first finalizes the attempt as expired, scores all saved responses, and rejects further edits. Saved responses are retained and reviewed like a submitted attempt.
4. Before the deadline, student submission finalizes and scores atomically. `submitted_at` records student submission; `finalized_at` records the terminal transition for either submitted or expired attempts.
5. Repeated answer saves update the single attempt/question response. Repeated submission returns the same persisted result and cannot create duplicate results.
6. Result scores/counts and answer explanations are immediately available after finalization. No pause or extension behavior is supported.
7. Test identity/description/duration and question/scoring content are locked after the first attempt starts. Staff can still close or unpublish a test for new starts; existing attempts remain available until their own deadline. Editorial revisions use new Question and MockTest records; immutable version/snapshot tables are deferred unless evidence shows this workflow is insufficient.

## Authentication and authorization

- Use the established Django built-in user model, authentication, and permissions. Student registration and account behavior follow Decision 0005; do not replace the user model without a reviewed, data-preserving migration and explicit approval.
- Anonymous access is limited to public content and test descriptions.
- Every attempt read/write and protected download checks the authenticated user's ownership or an explicit staff permission on the server.
- Staff-only content and question management use explicit staff permissions.
- Future paid access is based on server-verified entitlements, not browser state or client-supplied price/access values. Payment processing and paid access remain out of scope until their separately approved phase.

### Accounts and shared access policy (Decision 0005)

- Preserve Django's built-in user model. Do not add a profile table unless a concrete account requirement needs persistent fields beyond the existing user record.
- `access_control.user_can_access()` is the shared server-side decision point for published public resources and future restricted resources. Unpublished content is always denied; restricted access requires a verified server-side entitlement.
- `access_control.user_has_entitlement()` returns false until a future approved entitlement store exists. Current mock tests and published public educational files remain public according to their existing publication/visibility rules; restricted files remain inaccessible.
- Payment processing and entitlement grants are out of scope. Future provider webhooks must be verified and idempotent, and only confirmed transaction records may grant entitlements.

## Public and protected files

- Public educational downloads may be delivered from public storage.
- Protected files require an authorization check before the file is delivered or a short-lived storage URL is issued.
- A concealed link or filename is not an authorization mechanism.
- Phase 2 file metadata distinguishes `public` from `restricted`. Only published resources with a public file are served by the public PDF/download endpoint. Restricted files remain outside public web roots and receive no public delivery route in this phase; authorization-gated delivery is reserved for the approved `file_delivery` boundary.
- The initial deployment must not expose `MEDIA_ROOT` through Nginx or another static URL mapping. Production object-storage routing is a separate deployment decision.
- File type, size, retention, malware scanning needs, and user upload support are open decisions; avoid user uploads unless a feature requires them.

## Future memberships and payments

- The future payment phase may support paid tests or time-bound memberships.
- Payment records must track provider reference, amount/currency, status, timestamps, and a reconciliation-safe identifier without storing card data.
- Provider callbacks are verified server-side and processed idempotently. An entitlement is granted only after confirmed payment state.
- Pricing, refund, cancellation, renewal, tax, supported providers, and failed-payment policy are unresolved and out of current scope.

## Traceability

Architecture and boundaries are in [ARCHITECTURE.md](../../ARCHITECTURE.md); entity relationships are in [data-model.md](data-model.md); security behavior is in [security-requirements.md](security-requirements.md); phase gates are in [DEVELOPMENT_ROADMAP.md](../../DEVELOPMENT_ROADMAP.md).
