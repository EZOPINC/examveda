"""Render published resources, protected staff previews and public PDFs.

All public queries begin from published pages; file access repeats that check
and never serves restricted files or maps MEDIA_ROOT into a public URL.
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.cache import cache_control

from access_control.services import user_can_access

from .models import ContentPage, ExamCategory, ExamStage, ResourceFile, ResourceMetadata, Subject, Topic


PAGE_SIZE = 12


def _published_pages():
    """Return pages currently visible to anonymous visitors."""
    return ContentPage.objects.filter(is_published=True, published_at__lte=timezone.now()).select_related("resource", "resource__category", "resource__stage", "resource__subject", "resource__topic")


def _listing(request, queryset, title):
    """Render a paginated published-page listing."""
    page = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "content/resource_list.html", {"page_obj": page, "resources": page.object_list, "listing_title": title})


def resource_list(request):
    """List all published educational pages."""
    return _listing(request, _published_pages(), "Free learning resources")


def category_list(request, exam_slug):
    """List published resources for an exam category."""
    category = get_object_or_404(ExamCategory, slug=exam_slug, is_active=True)
    return _listing(request, _published_pages().filter(resource__category=category), category.name)


def stage_list(request, exam_slug, stage_slug):
    """List published resources for one exam stage."""
    category = get_object_or_404(ExamCategory, slug=exam_slug, is_active=True)
    stage = get_object_or_404(ExamStage, category=category, slug=stage_slug)
    return _listing(request, _published_pages().filter(resource__stage=stage), f"{category.name}: {stage.name}")


def year_list(request, exam_slug, stage_slug, year):
    """List resources for an exam stage and year."""
    stage = get_object_or_404(ExamStage, category__slug=exam_slug, category__is_active=True, slug=stage_slug)
    return _listing(request, _published_pages().filter(resource__stage=stage, resource__year=year), f"{stage.name} {year}")


def type_list(request, exam_slug, stage_slug, year, resource_type):
    """List resources matching a controlled resource type."""
    if resource_type not in ResourceMetadata.ResourceType.values:
        raise Http404
    stage = get_object_or_404(ExamStage, category__slug=exam_slug, category__is_active=True, slug=stage_slug)
    return _listing(request, _published_pages().filter(resource__stage=stage, resource__year=year, resource__resource_type=resource_type), f"{resource_type.replace('-', ' ').title()} {year}")


def resource_detail(request, exam_slug, stage_slug, year, resource_type, resource_slug):
    """Show one published resource at its canonical exam URL."""
    page = get_object_or_404(_published_pages(), slug=resource_slug, resource__category__slug=exam_slug, resource__stage__slug=stage_slug, resource__year=year, resource__resource_type=resource_type)
    return render(request, "content/resource_detail.html", {"content_page": page})


def subject_list(request, subject_slug):
    """List published resources for an active subject."""
    subject = get_object_or_404(Subject, slug=subject_slug, is_active=True)
    return _listing(request, _published_pages().filter(resource__subject=subject), subject.name)


def topic_list(request, subject_slug, topic_slug):
    """List published resources for one topic under its subject."""
    topic = get_object_or_404(Topic, subject__slug=subject_slug, subject__is_active=True, slug=topic_slug)
    return _listing(request, _published_pages().filter(resource__topic=topic), topic.name)


def editorial_detail(request, page_slug):
    """Show an unclassified published editorial page."""
    page = get_object_or_404(_published_pages(), slug=page_slug)
    return render(request, "content/resource_detail.html", {"content_page": page})


@staff_member_required
def preview_page(request, page_id):
    """Allow staff to preview draft or published content without publishing it."""
    page = get_object_or_404(ContentPage, pk=page_id)
    if not request.user.has_perm("content.view_contentpage"):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    return render(request, "content/resource_detail.html", {"content_page": page, "is_preview": True})


@cache_control(private=True, no_store=True)
def public_file(request, file_id):
    """Stream a PDF only when its resource is published and explicitly public."""
    resource_file = get_object_or_404(ResourceFile.objects.select_related("resource__page"), pk=file_id)
    page = resource_file.resource.page
    if not user_can_access(
        request.user,
        is_published=bool(page.is_published and page.published_at and page.published_at <= timezone.now()),
        is_public=resource_file.visibility == ResourceFile.Visibility.PUBLIC,
    ):
        raise Http404
    if not resource_file.file:
        raise Http404
    return FileResponse(resource_file.file.open("rb"), content_type="application/pdf", filename=resource_file.original_filename or "resource.pdf", as_attachment=False)
