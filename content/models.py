"""Store public educational pages, taxonomy and attached-file metadata.

The content views and Django admin depend on these models. File objects live
under MEDIA_ROOT, which must not be mapped to a public web server location.
"""

from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class ExamCategory(models.Model):
    """Represent an exam family such as WBCS."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "exam categories"

    def __str__(self):
        """Return the editorial category name."""
        return self.name


class ExamStage(models.Model):
    """Represent a stage belonging to one exam category."""

    category = models.ForeignKey(ExamCategory, on_delete=models.CASCADE, related_name="stages")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [models.UniqueConstraint(fields=["category", "slug"], name="content_stage_category_slug_uniq")]

    def __str__(self):
        """Return the stage name with its exam category."""
        return f"{self.category}: {self.name}"


class Subject(models.Model):
    """Provide shared subject taxonomy for resources and later questions."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        """Return the subject name."""
        return self.name


class Topic(models.Model):
    """Organize subject material into optional nested topics."""

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="topics")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [models.UniqueConstraint(fields=["subject", "slug"], name="content_topic_subject_slug_uniq")]

    def clean(self):
        """Ensure a parent belongs to this subject and cannot form a cycle."""
        super().clean()
        if self.parent_id and self.subject_id and self.parent.subject_id != self.subject_id:
            raise ValidationError({"parent": "Parent topic must belong to the same subject."})
        ancestor = self.parent
        while ancestor is not None:
            if self.pk and ancestor.pk == self.pk:
                raise ValidationError({"parent": "A topic cannot be its own ancestor."})
            ancestor = ancestor.parent

    def __str__(self):
        """Return a readable subject and topic label."""
        return f"{self.subject}: {self.name}"


class ContentPage(models.Model):
    """Hold the canonical body and publication lifecycle for a content page."""

    class Language(models.TextChoices):
        ENGLISH = "en", "English"
        BENGALI = "bn", "Bengali"

    title = models.CharField(max_length=240)
    slug = models.SlugField(max_length=180, unique=True)
    summary = models.CharField(max_length=500, blank=True)
    body = models.TextField()
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.ENGLISH)
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    seo_title = models.CharField(max_length=title.max_length, blank=True)
    seo_description = models.CharField(max_length=320, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_content_pages")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_content_pages")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "title"]
        indexes = [models.Index(fields=["is_published", "-published_at"], name="content_page_published_idx")]

    def clean(self):
        """Require publish time and non-empty body before publication."""
        super().clean()
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        if self.is_published and not self.body.strip():
            raise ValidationError({"body": "Published pages must have content."})

    def save(self, *args, **kwargs):
        """Set a publication timestamp when a valid page is published."""
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        """Return the page title."""
        return self.title


class ResourceMetadata(models.Model):
    """Classify an editorial page as an exam, subject or topic resource."""

    class ResourceType(models.TextChoices):
        ARTICLE = "articles", "Articles"
        NOTES = "notes", "Notes"
        STUDY_MATERIAL = "study-material", "Study materials"
        PREVIOUS_QUESTIONS = "previous-questions", "Previous-year questions"
        SOLUTIONS = "solutions", "Solutions"

    page = models.OneToOneField(ContentPage, on_delete=models.CASCADE, related_name="resource")
    category = models.ForeignKey(ExamCategory, null=True, blank=True, on_delete=models.PROTECT, related_name="resources")
    stage = models.ForeignKey(ExamStage, null=True, blank=True, on_delete=models.PROTECT, related_name="resources")
    year = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1900), MaxValueValidator(2200)])
    resource_type = models.CharField(max_length=32, choices=ResourceType.choices, default=ResourceType.STUDY_MATERIAL)
    subject = models.ForeignKey(Subject, null=True, blank=True, on_delete=models.PROTECT, related_name="resources")
    topic = models.ForeignKey(Topic, null=True, blank=True, on_delete=models.PROTECT, related_name="resources")

    class Meta:
        indexes = [
            models.Index(fields=["category", "stage", "year", "resource_type"], name="content_resource_archive_idx"),
            models.Index(fields=["subject", "topic"], name="content_resource_subject_idx"),
        ]

    def clean(self):
        """Validate stage/category and topic/subject taxonomy consistency."""
        super().clean()
        if self.stage_id and self.category_id and self.stage.category_id != self.category_id:
            raise ValidationError({"stage": "Stage must belong to the selected exam category."})
        if self.topic_id and self.subject_id and self.topic.subject_id != self.subject_id:
            raise ValidationError({"topic": "Topic must belong to the selected subject."})

    def __str__(self):
        """Return the resource title."""
        return self.page.title


class ResourceFile(models.Model):
    """Store PDF metadata and visibility without exposing media paths directly."""

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        RESTRICTED = "restricted", "Restricted"

    resource = models.ForeignKey(ResourceMetadata, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="content-files/%Y/%m/", validators=[FileExtensionValidator(["pdf"])])
    original_filename = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100, default="application/pdf", editable=False)
    size_bytes = models.PositiveBigIntegerField(default=0, editable=False)
    visibility = models.CharField(max_length=12, choices=Visibility.choices, default=Visibility.PUBLIC)
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "id"]

    def clean(self):
        """Limit PDF size and reject metadata that is not a PDF."""
        super().clean()
        if self.file:
            suffix = Path(self.file.name).suffix.lower()
            if suffix != ".pdf":
                raise ValidationError({"file": "Only PDF documents are accepted."})
            if self.file.size > 25 * 1024 * 1024:
                raise ValidationError({"file": "PDF documents must be 25 MB or smaller."})
            # Extensions and browser MIME labels are user-controlled; verify the file signature.
            self.file.seek(0)
            header = self.file.read(1024)
            self.file.seek(0)
            if b"%PDF-" not in header:
                raise ValidationError({"file": "The uploaded document does not have a PDF signature."})

    def save(self, *args, **kwargs):
        """Capture source name and size for admin display and delivery headers."""
        if self.file:
            self.size_bytes = self.file.size
            if not self.original_filename:
                self.original_filename = Path(self.file.name).name
        super().save(*args, **kwargs)

    def __str__(self):
        """Return the stored source filename."""
        return self.original_filename or Path(self.file.name).name
