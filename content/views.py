"""Render published resources, protected staff previews and public PDFs.

All public queries begin from published pages; file access repeats that check
and never serves restricted files or maps MEDIA_ROOT into a public URL.
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Count, Max, Q
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
    """Show published exams and retain a list of general free resources."""
    visible_page = Q(
        resources__page__is_published=True,
        resources__page__published_at__lte=timezone.now(),
    )
    categories = ExamCategory.objects.filter(
        is_active=True,
    ).annotate(
        subject_count=Count("resources__subject", filter=visible_page, distinct=True),
        paper_count=Count("resources__page", filter=visible_page & Q(
            resources__resource_type=ResourceMetadata.ResourceType.PREVIOUS_QUESTIONS,
        ), distinct=True),
        material_count=Count("resources__page", filter=visible_page, distinct=True),
    ).filter(material_count__gt=0).order_by("display_order", "name")
    return render(request, "content/study_materials_landing.html", {
        "categories": categories,
        "resources": _published_pages().exclude(
            resource__resource_type=ResourceMetadata.ResourceType.PREVIOUS_QUESTIONS,
        ).order_by("title")[:12],
    })


def category_list(request, exam_slug):
    """Show an exam and the subjects with published material under it."""
    category = get_object_or_404(ExamCategory, slug=exam_slug, is_active=True)
    subjects = Subject.objects.filter(
        is_active=True,
        resources__category=category,
        resources__page__is_published=True,
        resources__page__published_at__lte=timezone.now(),
    ).annotate(
        paper_count=Count("resources__page", filter=Q(
            resources__category=category,
            resources__resource_type=ResourceMetadata.ResourceType.PREVIOUS_QUESTIONS,
            resources__page__is_published=True,
            resources__page__published_at__lte=timezone.now(),
        ), distinct=True),
        latest_year=Max("resources__year", filter=Q(
            resources__category=category,
            resources__resource_type=ResourceMetadata.ResourceType.PREVIOUS_QUESTIONS,
            resources__page__is_published=True,
            resources__page__published_at__lte=timezone.now(),
        )),
    ).distinct().order_by("name")
    resources = _published_pages().filter(resource__category=category).exclude(
        resource__resource_type=ResourceMetadata.ResourceType.PREVIOUS_QUESTIONS,
        resource__subject__isnull=False,
    ).order_by("title")
    return render(request, "content/study_materials_exam.html", {
        "category": category,
        "subjects": subjects,
        "resources": resources,
    })


def exam_subject_list(request, exam_slug, subject_slug):
    """List published previous-year papers for one subject within an exam."""
    category = get_object_or_404(ExamCategory, slug=exam_slug, is_active=True)
    subject = get_object_or_404(Subject, slug=subject_slug, is_active=True)
    papers = _published_pages().filter(
        resource__category=category,
        resource__subject=subject,
        resource__resource_type=ResourceMetadata.ResourceType.PREVIOUS_QUESTIONS,
    ).order_by("-resource__year", "title")
    if not papers.exists() and not ResourceMetadata.objects.filter(
        category=category, subject=subject, page__is_published=True,
        page__published_at__lte=timezone.now(),
    ).exists():
        raise Http404
    return render(request, "content/study_materials_subject.html", {
        "category": category,
        "subject": subject,
        "papers": papers,
    })


def stage_list(request, exam_slug, stage_slug):
    """Keep the approved stage archive while resolving exam-scoped subjects."""
    category = get_object_or_404(ExamCategory, slug=exam_slug, is_active=True)
    stage = ExamStage.objects.filter(category=category, slug=stage_slug).first()
    if stage is None:
        return exam_subject_list(request, exam_slug, stage_slug)
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


def previous_paper_detail(request, exam_slug, subject_slug, paper_slug):
    """Show one published previous-year paper and its original demo content."""
    page = get_object_or_404(
        _published_pages(),
        slug=paper_slug,
        resource__category__slug=exam_slug,
        resource__category__is_active=True,
        resource__subject__slug=subject_slug,
        resource__subject__is_active=True,
        resource__resource_type=ResourceMetadata.ResourceType.PREVIOUS_QUESTIONS,
    )
    return render(request, "content/resource_detail.html", {
        "content_page": page,
        "paper_category": page.resource.category,
        "paper_subject": page.resource.subject,
        "is_demo": page.slug.startswith("demo-"),
    })


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
