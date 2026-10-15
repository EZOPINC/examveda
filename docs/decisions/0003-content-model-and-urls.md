# Decision 0003: Free Content Model and Public URLs

- **Status:** Approved and implemented; Phase 2 owner approval recorded 2026-10-15
- **Date:** 2026-10-15
- **Scope:** Content taxonomy, public URL structure, and file visibility boundaries

## Decision

Use the approved content entities `ExamCategory`, `ExamStage`, `Subject`, `Topic`, `ContentPage`, `ResourceMetadata`, and `ResourceFile`. `ContentPage` owns the canonical page body, slug, language, publication state, and SEO metadata. `ResourceMetadata` optionally classifies a page as an exam resource; `ResourceFile` records attached document metadata and whether the document is public or restricted.

Use the canonical public routes documented in `docs/requirements/functional-requirements.md` and `docs/requirements/data-model.md`, including year/type archive paths and an additional slug for a single resource. Subject and topic listings have explicit route segments to avoid collision with exam and resource slugs.

Only published pages are visible publicly. Draft preview requires staff authorization. Public file delivery requires both a published resource and a public file classification. Restricted files are stored outside public web roots and receive no public route in this phase; an authorization-aware `file_delivery` feature is deferred. Inline PDF viewing is a convenience, not copy protection.

## Rationale

Separating editorial page content from optional resource classification avoids duplicating publication and body fields. Explicit category and stage records model the suggested WBCS/prelims/year structure, while subject and topic taxonomy can also serve future questions. The canonical URLs support stable resource pages and useful archive/filter pages without introducing a front-end framework. Keeping restricted files unserved avoids creating a security promise before the access-control and file-delivery workflows exist.

## Consequences and validation

- Model/form validation must ensure a stage belongs to its exam category and a topic belongs to its subject.
- Public listings need pagination and database queries scoped to published pages; test that draft pages and their file endpoints remain inaccessible.
- Indexes should match measured/defined listing filters and use meaningful names.
- Review generated migrations before applying them; do not alter or delete existing databases.
- Revisit route patterns only through a reviewed URL/data migration plan because public URLs are stable interfaces.
