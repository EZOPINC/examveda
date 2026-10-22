# Decision 0006: Blog and Social Integration

**Status:** Implemented as an additive extension on 2026-10-22.

## Context

The project needs public editorial articles, category browsing and social sharing while keeping its Django monolith, the existing content publication rules, and lightweight browser-side behavior. Exam `Topic` is tied to `Subject`, so it is not suitable for general blog categories.

## Decision

- Reuse `ContentPage` as the canonical article body and publication record. Add nullable `BlogCategory`, `author_name`, `featured_image`, and `featured_image_alt` fields; create `BlogCategory` as the only new content entity.
- Keep existing `/free-resources/` routes and add `/blog/`, `/blog/category/<slug>/`, and `/blog/<slug>/` routes within the existing `content` application.
- Deliver blog images through Django views that recheck publication and file signatures, rather than exposing media storage directly. Staff previews use the existing staff permission boundary and private/no-store response headers.
- Use Django's built-in sitemap framework for published blog articles and categories with published articles. Emit Article JSON-LD only for a public published article.
- Configure optional social profile URLs through environment values. Render only HTTPS URLs, use safe external-link attributes, and provide browser-native share plus accessible copy controls without social-feed scripts.

## Rationale and alternatives

Reusing `ContentPage` avoids a second article body, slug, publication and SEO lifecycle and aligns with current admin preview and publication behavior. A separate `BlogCategory` is justified because the existing subject/topic taxonomy models curriculum content rather than editorial groupings. A separate blog application or CMS would duplicate workflows and add operational cost. Uploaded images remain in existing local media storage with checked application delivery because there is no approved object-storage integration.

## Consequences and change evidence

Migration `content.0002` is additive, changes no existing records and creates no sample articles. Apply it only through the normal reviewed deployment migration procedure. Reconsider a separate content store if editorial workflows require independent permissions, revisions, translations, or measured throughput that `ContentPage` cannot support. Reconsider image processing/storage only if upload volume, image performance, or security review provides evidence for it. Social-provider embeds require a separate privacy and performance review.
