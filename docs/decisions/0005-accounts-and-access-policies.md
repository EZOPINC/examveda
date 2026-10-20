# Decision 0005: Accounts and Access Policies

- **Status:** Owner-authorized for Phase 4 implementation
- **Date:** 2026-10-20
- **Scope:** Student registration, account maintenance, administrator roles, shared access decisions, and future entitlement integration

## Decision

Keep Django's established user model and authentication system. Public registration creates an ordinary active student account with username and password and signs the student in. Registration cannot set `is_staff`, `is_superuser`, groups, or permissions. Staff and administrator access is granted only through Django admin or trusted operator commands. No custom role framework, profile model, or user-model migration is introduced.

Students can view and update only their own account email, change their password while authenticated, and view their own attempts. Account recovery for a lost password is administrator-assisted after identity verification. Self-service email reset is deferred until verified-email handling and a production mail-delivery configuration are approved; an unverified address must not become an account recovery credential.

The `access_control` app exposes `user_can_access()` for published public resources and future entitlement-gated resources, plus `user_has_entitlement()` as the server-side lookup seam. Public resources pass when published. Unpublished and restricted resources fail closed. Because no verified entitlement records or payment confirmation flow exist, `user_has_entitlement()` returns false in this phase. Restricted files remain unavailable through public routes, and all current mock tests remain public.

## Rationale

Django's built-in user, forms, password validators, sessions, and admin already meet the current identity and administrator needs. Keeping the model avoids schema migration risk. A shared access service is justified because both public file delivery and exam availability need the same distinction between published public resources and future restricted resources. A single policy predicate is sufficient; a general role/permission framework is not.

## Future paid access

The later paid-access phase must define persistent entitlement records and their owner, code/resource scope, effective interval, revocation state, and source transaction. Only a verified provider webhook may confirm payment state and trigger an idempotent entitlement grant. Browser redirects, submitted form fields, or client-side state never grant access. Integrations must call the existing `user_can_access()` boundary and verify access after expiry or revocation.

## Consequences and verification

- No Django model or migration is added in Phase 4.
- Public content and mock-test descriptions stay readable anonymously; attempt and account pages require authentication and remain owner-scoped.
- Django admin remains restricted to active staff accounts and uses per-model permissions for management actions.
- Tests cover registration privilege boundaries, login/logout, password changes, account ownership, admin access, public access, and restricted-access denial.
- If self-service recovery is required for launch, first approve email verification and configure and verify production mail delivery. If paid access is introduced, approve the entitlement schema and webhook processing before changing the fail-closed lookup.
