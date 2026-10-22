# Security Requirements

**Status:** Baseline for all phases. Phases 3 and 4 are owner-approved. Phase 5 review findings and operational blockers are recorded in the [security and reliability report](../security/phase-5-security-reliability-report.md); deployment and payment controls remain future gates.

## Identity and sessions

- Use Django's password hashing, authentication, session, CSRF, and permission mechanisms.
- Use the established Django user model and password validators. Public registration cannot assign staff status, groups, or permissions.
- Students may change their password only through Django's authenticated password-change flow. Lost-password recovery is administrator-assisted after identity verification until email verification and production mail delivery are approved and configured.
- Do not treat an arbitrary, unverified account email as proof of identity or as a password-reset destination.
- Use HTTPS in deployed environments; configure secure cookies, allowed hosts, and production debug settings appropriately.
- Do not expose passwords, session identifiers, reset tokens, API secrets, or unnecessary personal information in logs or responses.

## Authorization and data privacy

- Check authorization on the server for every protected object and state-changing action.
- Use `access_control.user_can_access()` for shared public/restricted resource decisions. The current entitlement lookup is fail-closed; no browser-provided field, payment redirect, or unverified callback can grant access.
- Keep account/profile and attempt history queries scoped to the authenticated owner. Django admin access requires an active staff account and per-model permission for edits.
- Scope attempt access to the owner and explicitly permitted staff. Never rely on an identifier being hard to guess.
- Enforce test availability and eligibility on the server. Do not trust client-provided ownership, score, entitlement, price, or timestamps.
- Do not expose answer keys, explanations, private tests, unpublished materials, or another student's attempt through HTML, JavaScript, APIs, exports, or logs before policy permits it.
- Store one correct-answer key on the stable shared `QuestionOption`; localized option labels must reference that option identity and cannot define or change correctness. Keep locale selection server-side on `TestAttempt` and never let a language switch alter saved response IDs, test timing, or score state.
- Fail closed when a test locale, question prompt, option label, required explanation, or translated test metadata is missing or unpublished. Never fill a missing translation from another language. Existing attempts may continue to render their already-selected text after a locale is closed, while new starts and switches require a currently published, complete variant.
- Treat all Hindi/Bengali user-facing strings and authored question text as UTF-8. Verify stored and rendered Unicode through the configured PostgreSQL database before release; SQLite-only checks do not establish PostgreSQL encoding behavior.
- Define collection, retention, deletion, and access rules for personal and attempt data before production.

## Exam integrity and request handling

- Server-recorded timestamps determine duration, expiry, and submission state. Client timers are display only.
- Autosave and submit endpoints authenticate, verify ownership and lifecycle state, validate question membership and response data, and are safe to retry.
- Calculate scores on the server. Use transactions and database constraints for race-sensitive invariants and finalization.
- Lock the attempt row during answer updates and finalization. Lock the test row during start to serialize creation/resumption; enforce one active attempt per student/test in the database.
- Lock test/question editorial data after an attempt starts so later edits cannot alter historical scoring or answer review.
- At or after the server deadline, finalize saved responses as expired before returning the attempt; reject late saves regardless of the browser timer. Every attempt endpoint checks expiry, so no background worker is required for correctness.
- Define boundary behavior for simultaneous save/submit, expiry, network retries, and duplicate requests; cover it with automated tests before release.
- Rate-limit or otherwise protect sensitive authentication and high-impact endpoints when measured or threat-reviewed need warrants it; select mechanisms that fit the deployment rather than adding infrastructure without evidence.

## Input, browser, and dependency security

- Validate all server-side input and use Django's template escaping and safe query APIs.
- Keep CSRF protection enabled for state-changing browser requests. Use secure headers and content security policy after reviewing required inline scripts and third-party resources.
- Keep dependencies to the approved baseline, pin compatible versions, and update through reviewed changes and tests. Do not add a framework or service without a documented need.
- Treat uploaded files as untrusted if uploads are introduced; define type/size validation, storage isolation, scanning need, and delivery policy before enabling them.
- Blog featured images are limited to JPG/PNG/WebP and 5 MB, checked against file signatures, and served by an application route rather than a public media alias. The route rechecks article publication; staff preview images require staff permission and use private/no-store and `X-Robots-Tag: noindex` headers. This does not constitute malware scanning; keep host/storage isolation and review scanning if volume or threat evidence warrants it.
- Blog Article JSON-LD is emitted only for currently published articles and escapes HTML-sensitive JSON characters. Draft preview metadata is generic and noindex. Sitemap queries use the same publication/time boundary as public pages.
- Configured social URLs are rendered only for HTTPS destinations with a hostname and without embedded user credentials; external links use `noopener noreferrer`. No external social scripts or feed embeds are loaded.

## File and object storage security

- Separate public educational objects from protected objects by access policy and storage configuration.
- Authorize before returning a protected file or issuing a short-lived signed URL. Do not expose storage credentials or treat obscure URLs as authorization.
- Avoid caching protected files publicly. Set appropriate content type and download behavior; review private caching and expiration.
- Restrict object-storage and backup credentials to necessary operations and keep them out of source control.

## Future payment security

- Do not store card numbers or security codes.
- Verify payment-provider callbacks and signatures server-side; validate amount, currency, and transaction reference against the expected order.
- Make callback handling idempotent and auditable. Grant/revoke entitlements based on verified transaction state, not browser redirects.
- Define reconciliation, refund, cancellation, and retention procedures before paid access launches.

## Deployment, backups, and operations

- Keep PostgreSQL inaccessible from the public internet and restrict host/firewall access to required services.
- Provide production secrets through deployment environment or an appropriate secret store. `.env.example` must contain placeholders only.
- Require HTTPS, secure production settings, least-privilege service accounts, and reviewed OS/application updates.
- Back up PostgreSQL on a defined schedule to a separate failure domain where practical, define retention, protect backup access, and rehearse restoration. A successful backup job alone is not evidence of recoverability.
- Monitor service health, errors, disk and database capacity, and backup completion. Logs must be useful for troubleshooting without collecting secrets or excess personal data.
- Document incident response, credential rotation, restore, and rollback steps before production use.

## Security verification gates

- Content phase: unpublished content and protected downloads are inaccessible anonymously.
- Exam phase: cross-user attempt access is denied; malformed responses are rejected; expiry, duplicate save/submission, score authority, and answer reveal behavior are tested.
- Multilingual exam extension: only complete and published variants are advertised or selected; stable option correctness is shared; switching locale preserves answer IDs and server timestamps; UTF-8 round-trip is verified against PostgreSQL before deployment.
- Accounts/access phase: permission and entitlement boundaries are tested, including revoked/expired access.
- Deployment phase: HTTPS and secure settings are checked, database exposure is reviewed, backup restore is demonstrated, and secrets are absent from tracked files and logs.
- Before launch: conduct a focused threat review of account recovery, admin permissions, file delivery, and exam answer exposure; track findings and remediation.
