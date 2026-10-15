# Functional Requirements

**Status:** Phase 0 baseline; Phase 2 free-content requirements and URL scheme approved and implemented. Product policies marked open must be decided before the affected feature is implemented.

## Roles and journeys

### Visitor and student

- A visitor can browse published free articles, notes, study materials, previous-year questions, solutions, and public test descriptions without an account.
- A visitor can register, sign in, and sign out. Registration and account recovery details must be finalized before the accounts phase.
- An authenticated student can start an available test, answer questions, save responses, resume an eligible attempt, submit, and view permitted results.
- A student can view only their own attempt history and details.
- A student can access protected materials only when the configured access rule grants it.
- A student can use core pages and exam controls on a mobile device and on a slower connection; the server remains authoritative if browser requests are delayed.

### Administrator and editor

- Authorized staff can create, edit, preview, publish, unpublish, and archive educational content.
- Authorized staff can create and maintain subjects, topics, questions, options, explanations, tests, ordering, duration, scoring, availability, and review policy.
- Staff permissions should distinguish administration from ordinary student capabilities. The initial editorial workflow may use Django admin; a custom interface needs a demonstrated requirement.
- Editing published questions or tests must not silently alter existing attempt results. Versioning or snapshots must be selected before exam implementation.

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
- `/mock-tests/` and `/mock-tests/<test-slug>/` remain reserved for the exam engine and are not implemented in this phase.
- Category, stage, year, resource type, subject, and topic pages list only published content. An empty or unknown filter returns a normal not-found response rather than revealing draft records.
- Content can be authored in Bengali or English. Language selection, search behavior, and whether individual resources can have parallel translations remain open decisions.
- Only published items intended for public access are visible to anonymous visitors. Preview and draft routes require staff authorization.
- Staff preview requires an authenticated staff account and is served through a protected application view; an unpublished page or its files are never exposed by a public detail or PDF route.
- Public content pages should include descriptive titles and metadata suitable for search indexing; private student data and attempts must not be indexed.
- Public PDF resources may be displayed inline in a browser where supported. Browser display cannot prevent saving, printing, screenshots, or copying; do not promise copy protection.

## Questions, tests, attempts, and responses

- A question belongs to the appropriate subject/topic taxonomy and contains prompt content, answer options, explanation, language, and publication state.
- A test defines ordered questions, duration, availability, scoring rules, and result-review policy. These values must be validated server-side.
- The platform supports an attempt tied to its student and test. The exact retake/attempt limit is an open policy.
- A response records the student's selected option or options and server-managed save/update times. Question type and whether multiple selections are allowed must be explicit in the test/question design.
- The server calculates marks from stored responses and the configured scoring policy. The browser cannot provide authoritative marks or correct answers.
- Result display may include score, correct/incorrect/unanswered counts, and explanations only when allowed by the review policy.

## Exam lifecycle

Proposed states: `in_progress`, `submitted`, and `expired`. A separate pre-start record is unnecessary unless a confirmed workflow requires it.

1. On start, the server checks authentication, availability, eligibility, and attempt limit, then records `started_at` and the server-computed `expires_at`.
2. The browser displays remaining time using server-provided timing data. It is not trusted to enforce duration.
3. Autosave verifies the authenticated owner, attempt state, expiry, question membership, and valid response data. Retries must not create duplicate responses.
4. Resume is allowed only for an owned, in-progress attempt that has not expired and remains eligible under the policy.
5. Submission verifies ownership and state, records a server timestamp, calculates and stores or reproducibly derives the result, and makes repeat submission requests safe.
6. At or after expiry, the server prevents further answer changes and finalizes the attempt as expired according to the agreed treatment of saved answers.
7. Result review reveals answer keys and explanations only at the configured review point.

Open decisions before implementation: whether expiry auto-submits saved responses, treatment of unanswered questions, negative marking, partial credit, late requests at the time boundary, test pause rules, retakes, and whether results are immediate or delayed.

## Authentication and authorization

- Use Django authentication and permissions. Decide whether a custom user model is justified before initial migrations.
- Anonymous access is limited to public content and test descriptions.
- Every attempt read/write and protected download checks the authenticated user's ownership or an explicit staff permission on the server.
- Staff-only content and question management use explicit staff permissions.
- Future paid access is based on server-verified entitlements, not browser state or client-supplied price/access values.

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
