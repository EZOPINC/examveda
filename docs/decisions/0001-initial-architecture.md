# Decision 0001: Initial Architecture

- **Status:** Accepted as the Phase 0 planning baseline
- **Date:** 2026-10-15
- **Decision owners:** Project owner
- **Implementation status:** Not implemented; application code and infrastructure remain out of scope

## Context

The project needs public bilingual learning materials, timed exams with trustworthy results, student accounts and history, staff content management, future paid access, mobile support, and an affordable OCI deployment path. The repository currently has no application code or dependencies. The approved project rules establish Django, PostgreSQL, server-rendered templates, vanilla JavaScript, Nginx, Gunicorn, OCI, and a modular monolith as the baseline.

The infrastructure target of INR 5,000–15,000 per month constrains planning but does not establish actual provider pricing, traffic capacity, availability, or recovery objectives.

## Decision

1. Use a modular Django monolith with PostgreSQL as the authoritative store.
2. Preserve the Django project package name `config` and the canonical application boundaries `accounts`, `content`, `exam_engine`, `access_control`, `payments`, and `file_delivery`; create apps only when their feature is approved.
3. Use Django templates and vanilla JavaScript for the initial user interface. Use Django `auth` and `admin` rather than duplicating them.
4. Keep exam duration, attempt state, ownership, answer keys, scoring, and submission authority on the server. Use server-recorded timestamps and retry-safe save/submission operations.
5. Keep public content and protected content/file delivery under distinct access rules. Authorize protected file delivery before returning content or a short-lived storage URL.
6. Plan for Linux OCI deployment with Nginx, Gunicorn, private PostgreSQL, HTTPS, environment-provided secrets, monitoring, and restorable backups. Evaluate the simplest hosting shape that meets verified reliability and budget needs.
7. Do not preemptively introduce a front-end framework, microservices, Redis, Celery, Kubernetes, a CDN, or multiple servers. Add only when requirements or measurements justify the operational cost.
8. Preserve existing code and names. Before any future change, inspect the repository and reuse established modules, variables, fields, URLs, and configuration keys. Add a new module or variable only for a documented requirement that an existing component cannot reasonably support; explain and approve structural changes through a decision record.

## Rationale

The monolith keeps deployment and maintenance manageable while content, accounts, and exam workflows are still being established. Django supplies authentication, admin, CSRF, templating, and ORM capabilities that fit the requirements without adding another framework. PostgreSQL supports relational integrity for attempts and responses. Server authority is necessary because client-controlled clocks and scores would undermine exam validity. Separating access policy from public routes and protecting file delivery addresses private attempts and future paid materials.

Starting with a measured, simple OCI topology respects the cost target while leaving room to split services later. The decision does not claim a particular topology can meet unknown concurrency, availability, or recovery targets.

## Alternatives considered

- **Separate services or microservices:** rejected for the initial stage because no independent scaling or ownership need is established and it increases deployment and operations complexity.
- **React or another front-end framework:** rejected initially because the required pages and interactions can be delivered with templates and vanilla JavaScript; reconsider only with demonstrated interaction/accessibility needs.
- **Redis/Celery and a CDN at launch:** deferred because there is no measured cache or background processing requirement yet.
- **Create all canonical apps immediately:** rejected because unused apps add structure without delivering behavior; canonical names remain reserved.
- **Separate database host from the outset:** left open for validation against actual OCI prices, availability expectations, and recovery needs.

## Consequences and follow-up

- Use Django's built-in user model for the foundation because no custom authentication identity fields are confirmed. Revisit only if confirmed account requirements justify a custom model, and before account features are built.
- The initial exam policies were later resolved and approved in [Decision 0004](0004-exam-engine-policies.md) before Phase 3 implementation: single-choice scoring, unlimited attempts, expiry handling, immediate finalized review, and a frozen authored graph without version/snapshot tables.
- Before production, obtain workload and recovery objectives, validate OCI costs, and rehearse backup restoration.
- Requirements and phase gates are maintained in `docs/requirements/` and `DEVELOPMENT_ROADMAP.md`.

## Revisit criteria

Reopen this decision when measured performance, availability/recovery objectives, team operations, verified hosting costs, confirmed product requirements, or a security review show that the current choice cannot meet needs. Any change must assess impacts on imports, migrations/data, URLs, tests, deployment, and operations and must preserve working behavior unless an approved migration plan says otherwise.
