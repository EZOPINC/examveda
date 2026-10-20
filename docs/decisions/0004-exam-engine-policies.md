# Decision 0004: Mock Exam Engine Policies

- **Status:** Owner-approved for Phase 3 implementation
- **Date:** 2026-10-20
- **Scope:** Question type, scoring, attempt lifecycle, result review, and historical integrity

## Decision

Phase 3 supports single-choice questions. A published question has at least two options and exactly one correct answer. Each test question specifies positive marks and negative marks from zero through the positive value. Correct earns positive marks, incorrect loses negative marks, and unanswered earns zero. There is no partial credit; aggregate scores may be negative.

Authenticated students have unlimited attempts. A start request resumes an existing unexpired attempt for the same student and test. Once an attempt is terminal, a later start creates a new attempt. Attempts cannot be paused or extended.

The server determines `started_at`, `expires_at`, submission, expiry, and score. The exact deadline is exclusive for answer changes: at `now >= expires_at`, the attempt expires, saved responses are scored, and no more changes are accepted. Expiry is finalized when an attempt endpoint observes the deadline; no background service is required for correctness. Student submission before the deadline records `submitted_at`; both terminal paths record `finalized_at`.

Repeated response saves update the one response row for that attempt/question. Repeated submissions return the stored terminal result and do not generate duplicate results. Score and correct/incorrect/unanswered totals are stored on `TestAttempt` in the finalization transaction. These results and the correct answer/explanation review are available immediately after finalization. Active exam responses never include answer-key fields.

Question content/options and test identity, description, duration, ordered questions, and scoring become immutable after the first attempt starts. Staff may still unpublish a test or adjust its availability window to stop new starts; an existing attempt remains resumable until its own deadline. Revisions to the frozen exam content use new Question and MockTest records. This avoids separate version/snapshot and result entities for the initial scope. `MockTestQuestion` is the explicit ordered join and stores per-test scoring. The student foreign key uses the established Django user model; registration and profiles remain in the accounts phase.

## Rationale

Single-choice and per-question scoring provide a clear first scoring rule and keep response integrity enforceable with one option foreign key. Freezing the authored graph preserves historical results without copying every prompt and answer into snapshots. Storing a single result on its attempt matches the one-to-one lifecycle. Row locks, uniqueness constraints, and server timestamps address retries and concurrent start/save/submit operations without Redis or background workers.

## Consequences and verification

- The `exam_engine` app contains only the question, option, test, ordered test-question, attempt, and response entities.
- Admin/model validation requires at least two options and one correct option for published or test-assigned questions; test duration is 1–240 minutes.
- A conditional uniqueness constraint permits at most one `in_progress` attempt for a student/test.
- Every attempt endpoint checks the database deadline. At or after expiry it finalizes the same attempt and prevents later mutations.
- Tests must cover ownership, answer persistence, repeat-safe submission, scoring, deadline boundaries, interrupted resumption, expiry, locked authoring, and answer-key withholding/release.
- If future question types, versioned editing, scheduled asynchronous expiry, or complex result audits are required, document evidence and a migration plan before changing this decision.
