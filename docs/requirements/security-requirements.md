# Security Requirements

**Status:** Phase 0 baseline. These requirements must be translated into implementation checks and operational procedures during the relevant approved phases.

## Identity and sessions

- Use Django's password hashing, authentication, session, CSRF, and permission mechanisms.
- Decide account verification, recovery, password policy, session lifetime, and custom-user needs before the accounts foundation is implemented.
- Use HTTPS in deployed environments; configure secure cookies, allowed hosts, and production debug settings appropriately.
- Do not expose passwords, session identifiers, reset tokens, API secrets, or unnecessary personal information in logs or responses.

## Authorization and data privacy

- Check authorization on the server for every protected object and state-changing action.
- Scope attempt access to the owner and explicitly permitted staff. Never rely on an identifier being hard to guess.
- Enforce test availability and eligibility on the server. Do not trust client-provided ownership, score, entitlement, price, or timestamps.
- Do not expose answer keys, explanations, private tests, unpublished materials, or another student's attempt through HTML, JavaScript, APIs, exports, or logs before policy permits it.
- Define collection, retention, deletion, and access rules for personal and attempt data before production.

## Exam integrity and request handling

- Server-recorded timestamps determine duration, expiry, and submission state. Client timers are display only.
- Autosave and submit endpoints authenticate, verify ownership and lifecycle state, validate question membership and response data, and are safe to retry.
- Calculate scores on the server. Use transactions and database constraints for race-sensitive invariants and finalization.
- Define boundary behavior for simultaneous save/submit, expiry, network retries, and duplicate requests; cover it with automated tests before release.
- Rate-limit or otherwise protect sensitive authentication and high-impact endpoints when measured or threat-reviewed need warrants it; select mechanisms that fit the deployment rather than adding infrastructure without evidence.

## Input, browser, and dependency security

- Validate all server-side input and use Django's template escaping and safe query APIs.
- Keep CSRF protection enabled for state-changing browser requests. Use secure headers and content security policy after reviewing required inline scripts and third-party resources.
- Keep dependencies to the approved baseline, pin compatible versions, and update through reviewed changes and tests. Do not add a framework or service without a documented need.
- Treat uploaded files as untrusted if uploads are introduced; define type/size validation, storage isolation, scanning need, and delivery policy before enabling them.

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
- Accounts/access phase: permission and entitlement boundaries are tested, including revoked/expired access.
- Deployment phase: HTTPS and secure settings are checked, database exposure is reviewed, backup restore is demonstrated, and secrets are absent from tracked files and logs.
- Before launch: conduct a focused threat review of account recovery, admin permissions, file delivery, and exam answer exposure; track findings and remediation.
