"""Provide staff editorial management and links to protected previews."""

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .forms import ContentPageForm, ResourceFileForm, ResourceMetadataForm, TopicForm
from .models import ContentPage, ExamCategory, ExamStage, ResourceFile, ResourceMetadata, Subject, Topic


class ResourceMetadataInline(admin.StackedInline):
    """Allow editors to classify a page in the same admin workflow."""

    model = ResourceMetadata
    extra = 0
    max_num = 1


@admin.register(ContentPage)
class ContentPageAdmin(admin.ModelAdmin):
    """Support draft editing, preview, publication and unpublication."""

    form = ContentPageForm
    list_display = ["title", "language", "is_published", "published_at", "updated_at"]
    list_filter = ["is_published", "language", "published_at"]
    search_fields = ["title", "slug", "summary", "body"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ResourceMetadataInline]
    readonly_fields = ["created_at", "updated_at", "preview_link"]
    fieldsets = [(None, {"fields": ("title", "slug", "summary", "body", "language")}), ("Publication and search", {"fields": ("is_published", "published_at", "seo_title", "seo_description", "preview_link")}), ("Audit", {"fields": ("created_by", "updated_by", "created_at", "updated_at"), "classes": ["collapse"]})]

    @admin.display(description="Staff preview")
    def preview_link(self, obj):
        """Link staff to the protected preview route for saved pages."""
        if not obj or not obj.pk:
            return "Save the page to preview it."
        return format_html('<a href="{}" target="_blank" rel="noopener">Preview page</a>', reverse("content:preview_page", args=[obj.pk]))

    def save_model(self, request, obj, form, change):
        """Record the staff editor for page audit fields."""
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        """Save optional classification entered alongside the content page."""
        super().save_related(request, form, formsets, change)


@admin.register(ResourceMetadata)
class ResourceMetadataAdmin(admin.ModelAdmin):
    """Manage optional exam, year, subject and topic classification."""

    form = ResourceMetadataForm
    list_display = ["page", "category", "stage", "year", "resource_type", "subject", "topic"]
    list_filter = ["category", "stage", "year", "resource_type", "subject"]
    search_fields = ["page__title", "page__slug"]


@admin.register(ResourceFile)
class ResourceFileAdmin(admin.ModelAdmin):
    """Manage PDF visibility metadata without exposing storage URLs."""

    form = ResourceFileForm
    list_display = ["original_filename", "resource", "visibility", "size_bytes"]
    list_filter = ["visibility"]
    readonly_fields = ["content_type", "size_bytes", "created_at"]


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    """Manage subject topics with taxonomy validation."""

    form = TopicForm
    list_display = ["name", "subject", "parent", "display_order"]
    list_filter = ["subject"]


admin.site.register([ExamCategory, ExamStage, Subject])
