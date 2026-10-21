"""Verify publication boundaries, canonical URLs and rendered content."""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from .models import ContentPage, ExamCategory, ExamStage, ResourceMetadata, Subject, Topic


class ContentPublicationTests(TestCase):
    """Exercise anonymous publication rules and authorized staff preview."""

    @classmethod
    def setUpTestData(cls):
        """Create representative Bengali and English resources for requests."""
        cls.category = ExamCategory.objects.create(name="WBCS", slug="wbcs")
        cls.stage = ExamStage.objects.create(category=cls.category, name="Prelims", slug="prelims")
        cls.subject = Subject.objects.create(name="History", slug="history")
        cls.topic = Topic.objects.create(subject=cls.subject, name="Modern India", slug="modern-india")
        cls.published = ContentPage.objects.create(title="WBCS 2024 Solutions", slug="wbcs-2024-solutions", body="Solution body", language="en", is_published=True, published_at=timezone.now())
        ResourceMetadata.objects.create(page=cls.published, category=cls.category, stage=cls.stage, year=2024, resource_type="solutions", subject=cls.subject, topic=cls.topic)
        cls.draft = ContentPage.objects.create(title="Draft notes", slug="draft-notes", body="Private draft")
        cls.user = get_user_model().objects.create_user(username="editor", password="secure-test-password", is_staff=True, is_superuser=True)

    def test_unpublished_page_is_not_available_through_public_routes(self):
        """Draft slugs must not disclose page content publicly."""
        response = self.client.get(reverse("content:editorial_detail", args=[self.draft.slug]))
        self.assertEqual(response.status_code, 404)

    def test_public_listing_and_canonical_resource_detail_render(self):
        """Published resources appear at the approved archive and detail URLs."""
        listing = self.client.get(reverse("content:type_list", args=["wbcs", "prelims", 2024, "solutions"]))
        detail = self.client.get(reverse("content:resource_detail", args=["wbcs", "prelims", 2024, "solutions", self.published.slug]))
        self.assertContains(listing, "WBCS 2024 Solutions")
        self.assertContains(detail, "Solution body")

    def test_draft_is_visible_only_in_staff_preview(self):
        """Staff can preview a draft while anonymous users cannot."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("content:preview_page", args=[self.draft.pk]))
        self.assertContains(response, "Private draft")
        self.assertContains(response, "not published publicly")

    def test_staff_without_content_permission_cannot_preview(self):
        """Staff status alone does not grant the content view permission."""
        editor = get_user_model().objects.create_user(username="staff-without-content-permission", password="secure-test-password", is_staff=True)
        self.client.force_login(editor)
        response = self.client.get(reverse("content:preview_page", args=[self.draft.pk]))
        self.assertEqual(response.status_code, 403)

    def test_topic_listing_does_not_include_draft_resources(self):
        """Topic archives only contain published resources."""
        response = self.client.get(reverse("content:topic_list", args=["history", "modern-india"]))
        self.assertContains(response, "WBCS 2024 Solutions")
        self.assertNotContains(response, "Draft notes")

    def test_publication_requires_body_and_sets_timestamp(self):
        """Publishing an empty page is rejected and valid publish time is recorded."""
        page = ContentPage(title="Empty", slug="empty", body="", is_published=True)
        with self.assertRaises(ValidationError):
            page.full_clean()
        page.body = "Ready"
        page.full_clean()
        self.assertIsNotNone(page.published_at)


class ContentRouteTests(TestCase):
    """Keep the approved archive and editorial paths stable."""

    def test_archive_and_editorial_url_patterns(self):
        """Reverse canonical public paths without hard-coded view URLs."""
        self.assertEqual(reverse("content:resource_list"), "/free-resources/")
        self.assertEqual(reverse("content:type_list", args=["wbcs", "prelims", 2024, "solutions"]), "/free-resources/wbcs/prelims/2024/solutions/")
        self.assertEqual(reverse("content:editorial_detail", args=["about-exam"]), "/free-resources/pages/about-exam/")


class ContentAdminJourneyTests(TestCase):
    """Exercise editorial creation, preview, publication and withdrawal."""

    def setUp(self):
        """Authenticate as an editor with normal admin content permissions."""
        self.editor = get_user_model().objects.create_superuser(username="admin-editor", email="editor@example.test", password="secure-test-password")
        self.client.force_login(self.editor)

    def test_editor_creates_previews_publishes_and_unpublishes_page(self):
        """Drive the admin add/change forms and confirm public transitions."""
        add_url = reverse("admin:content_contentpage_add")
        response = self.client.post(add_url, {
            "title": "Admin workflow article", "slug": "admin-workflow-article", "summary": "Admin journey", "body": "Draft content",
            "language": "en", "is_published": "", "published_at": "", "seo_title": "", "seo_description": "",
            "created_by": "", "updated_by": "", "_save": "Save",
            "resource-TOTAL_FORMS": "0", "resource-INITIAL_FORMS": "0", "resource-MIN_NUM_FORMS": "0", "resource-MAX_NUM_FORMS": "1",
        })
        self.assertEqual(response.status_code, 302, response.context and response.context[0].get("adminform"))
        page = ContentPage.objects.get(slug="admin-workflow-article")
        self.assertEqual(self.client.get(reverse("content:preview_page", args=[page.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("content:editorial_detail", args=[page.slug])).status_code, 404)

        change_url = reverse("admin:content_contentpage_change", args=[page.pk])
        publish = self.client.post(change_url, {
            "title": page.title, "slug": page.slug, "summary": page.summary, "body": page.body,
            "language": page.language, "is_published": "on", "published_at": "", "seo_title": "", "seo_description": "",
            "created_by": str(self.editor.pk), "updated_by": str(self.editor.pk), "_save": "Save",
            "resource-TOTAL_FORMS": "0", "resource-INITIAL_FORMS": "0", "resource-MIN_NUM_FORMS": "0", "resource-MAX_NUM_FORMS": "1",
        })
        self.assertEqual(publish.status_code, 302)
        page.refresh_from_db()
        self.assertTrue(page.is_published)
        self.assertIsNotNone(page.published_at)
        self.assertEqual(self.client.get(reverse("content:editorial_detail", args=[page.slug])).status_code, 200)

        withdraw = self.client.post(change_url, {
            "title": page.title, "slug": page.slug, "summary": page.summary, "body": page.body,
            "language": page.language, "is_published": "", "published_at": page.published_at.strftime("%Y-%m-%d %H:%M:%S"), "seo_title": "", "seo_description": "",
            "created_by": str(self.editor.pk), "updated_by": str(self.editor.pk), "_save": "Save",
            "resource-TOTAL_FORMS": "0", "resource-INITIAL_FORMS": "0", "resource-MIN_NUM_FORMS": "0", "resource-MAX_NUM_FORMS": "1",
        })
        self.assertEqual(withdraw.status_code, 302)
        self.assertEqual(self.client.get(reverse("content:editorial_detail", args=[page.slug])).status_code, 404)


class ResourceFileAccessTests(TestCase):
    """Keep restricted PDFs inaccessible and public delivery publication-aware."""

    @override_settings(MEDIA_ROOT="")
    def test_file_delivery_requires_public_classification_and_published_page(self):
        """Only public files attached to currently published pages stream."""
        with TemporaryDirectory() as media_dir:
            with self.settings(MEDIA_ROOT=Path(media_dir)):
                category = ExamCategory.objects.create(name="WBCS", slug="wbcs")
                stage = ExamStage.objects.create(category=category, name="Prelims", slug="prelims")
                page = ContentPage.objects.create(title="PDF resource", slug="pdf-resource", body="A PDF", is_published=True, published_at=timezone.now())
                metadata = ResourceMetadata.objects.create(page=page, category=category, stage=stage, year=2024)
                public_file = metadata.files.create(file=SimpleUploadedFile("public.pdf", b"%PDF-1.4 public", content_type="application/pdf"))
                restricted_file = metadata.files.create(file=SimpleUploadedFile("private.pdf", b"%PDF-1.4 private", content_type="application/pdf"), visibility="restricted")
                response = self.client.get(reverse("content:public_file", args=[public_file.pk]))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(b"%PDF-1.4 public" in b"".join(response.streaming_content))
                self.assertEqual(self.client.get(reverse("content:public_file", args=[restricted_file.pk])).status_code, 404)
                page.is_published = False
                page.save()
                self.assertEqual(self.client.get(reverse("content:public_file", args=[public_file.pk])).status_code, 404)


@override_settings(DEBUG=True)
class DemoStudyMaterialCommandTests(TestCase):
    """Keep explicit local demo seeding repeatable and non-destructive."""

    def test_command_can_run_repeatedly_without_duplicates(self):
        """Repeated explicit loads reuse matching stable-key records."""
        call_command("seed_demo_study_materials", stdout=StringIO())
        call_command("seed_demo_study_materials", stdout=StringIO())

        self.assertEqual(ExamCategory.objects.filter(slug__in=["wbpsc-clerkship", "wbcs"]).count(), 2)
        self.assertEqual(Subject.objects.filter(slug__in=["history", "general-studies", "mathematics", "geography"]).count(), 4)
        self.assertEqual(ContentPage.objects.filter(slug__startswith="demo-").count(), 12)
        self.assertEqual(ResourceMetadata.objects.filter(page__slug__startswith="demo-").count(), 12)

    def test_demo_paper_years_and_exam_subject_relationships_are_consistent(self):
        """Each configured exam/subject pair receives the two intended years."""
        call_command("seed_demo_study_materials", stdout=StringIO())

        expected_pairs = {
            "wbpsc-clerkship": {"history", "general-studies", "mathematics"},
            "wbcs": {"history", "geography", "general-studies"},
        }
        for exam_slug, subject_slugs in expected_pairs.items():
            for subject_slug in subject_slugs:
                years = set(ResourceMetadata.objects.filter(
                    category__slug=exam_slug,
                    subject__slug=subject_slug,
                    page__slug__startswith="demo-",
                ).values_list("year", flat=True))
                self.assertEqual(years, {2023, 2022})

    def test_command_refuses_to_overwrite_a_conflicting_record(self):
        """A stable slug owned by different editorial content raises an error."""
        ExamCategory.objects.create(slug="wbpsc-clerkship", name="Different existing exam")

        with self.assertRaises(CommandError):
            call_command("seed_demo_study_materials", stdout=StringIO())

        self.assertEqual(ExamCategory.objects.get(slug="wbpsc-clerkship").name, "Different existing exam")
        self.assertFalse(ContentPage.objects.filter(slug__startswith="demo-").exists())

    @override_settings(DEBUG=False)
    def test_command_is_disabled_when_debug_is_off(self):
        """Production-style settings cannot run the local seed command."""
        with self.assertRaises(CommandError):
            call_command("seed_demo_study_materials", stdout=StringIO())
        self.assertFalse(ExamCategory.objects.filter(slug="wbpsc-clerkship").exists())


@override_settings(DEBUG=True)
class DemoStudyMaterialNavigationTests(TestCase):
    """Verify the anonymous exam-to-subject-to-paper browsing journey."""

    @classmethod
    def setUpTestData(cls):
        """Load only the labelled local demo records into the isolated test DB."""
        call_command("seed_demo_study_materials", stdout=StringIO())

    def test_landing_page_lists_exams_and_counts_available_content(self):
        """The public landing links to both exams and previews subject/paper counts."""
        home = self.client.get(reverse("home"))
        self.assertContains(home, reverse("content:resource_list"))

        response = self.client.get(reverse("content:resource_list"))

        self.assertContains(response, "Free Study Materials")
        self.assertContains(response, "WBPSC Clerkship")
        self.assertContains(response, "WBCS")
        self.assertContains(response, "3 subjects")
        self.assertContains(response, "6 papers")
        self.assertContains(response, reverse("content:category_list", args=["wbpsc-clerkship"]))

    def test_exam_page_only_lists_subjects_within_that_exam(self):
        """Exam subject lists follow metadata's category relationship."""
        response = self.client.get(reverse("content:category_list", args=["wbpsc-clerkship"]))

        self.assertContains(response, "History")
        self.assertContains(response, "General Studies")
        self.assertContains(response, "Mathematics")
        self.assertNotContains(response, "Geography")
        self.assertContains(response, reverse("content:exam_subject_list", args=["wbpsc-clerkship", "history"]))

    def test_subject_page_lists_its_exam_papers_in_descending_year_order(self):
        """The selected exam and subject scope paper rows and year ordering."""
        response = self.client.get(reverse("content:exam_subject_list", args=["wbpsc-clerkship", "history"]))
        html = response.content.decode()

        self.assertContains(response, "WBPSC Clerkship")
        self.assertContains(response, "History — Previous-year Question Papers")
        self.assertLess(html.index("Demo Year 2023"), html.index("Demo Year 2022"))
        self.assertContains(response, reverse("content:previous_paper_detail", args=[
            "wbpsc-clerkship", "history", "demo-wbpsc-clerkship-history-2023-previous-question-paper",
        ]))

    def test_paper_detail_shows_demo_notice_questions_and_working_breadcrumbs(self):
        """The detail view labels the sample, renders original questions, and links back."""
        response = self.client.get(reverse("content:previous_paper_detail", args=[
            "wbpsc-clerkship", "history", "demo-wbpsc-clerkship-history-2023-previous-question-paper",
        ]))

        self.assertContains(response, "Demo record:")
        self.assertContains(response, "not an authentic or verified official WBPSC")
        self.assertContains(response, "Illustrative answer:")
        self.assertContains(response, "WBPSC Clerkship")
        self.assertContains(response, "History")
        self.assertContains(response, "2023")
        self.assertContains(response, reverse("content:resource_list"))
        self.assertContains(response, reverse("content:category_list", args=["wbpsc-clerkship"]))
        self.assertContains(response, reverse("content:exam_subject_list", args=["wbpsc-clerkship", "history"]))

    def test_subject_with_only_other_materials_shows_a_helpful_empty_paper_state(self):
        """A valid exam/subject can explain when no previous-year papers exist."""
        category = ExamCategory.objects.get(slug="wbpsc-clerkship")
        subject = Subject.objects.create(slug="civics-demo", name="Civics Demo")
        page = ContentPage.objects.create(
            title="Civics overview", slug="civics-overview", body="A published note.",
            is_published=True, published_at=timezone.now(),
        )
        ResourceMetadata.objects.create(
            page=page, category=category, subject=subject,
            resource_type=ResourceMetadata.ResourceType.NOTES,
        )

        response = self.client.get(reverse("content:exam_subject_list", args=[category.slug, subject.slug]))

        self.assertContains(response, "No published previous-year papers are available for this subject yet.")

    def test_subject_from_a_different_exam_is_not_listed_under_this_exam(self):
        """Shared global subjects only appear when metadata links this exam."""
        response = self.client.get(reverse("content:exam_subject_list", args=["wbcs", "mathematics"]))
        self.assertEqual(response.status_code, 404)

    def test_unpublished_papers_and_invalid_exam_subject_or_paper_slugs_are_hidden(self):
        """Draft records stay out of archives and unknown hierarchy keys return 404."""
        category = ExamCategory.objects.get(slug="wbpsc-clerkship")
        subject = Subject.objects.get(slug="history")
        draft = ContentPage.objects.create(title="Secret demo draft", slug="secret-demo-draft", body="Hidden")
        ResourceMetadata.objects.create(
            page=draft,
            category=category,
            subject=subject,
            year=2021,
            resource_type=ResourceMetadata.ResourceType.PREVIOUS_QUESTIONS,
        )

        subject_url = reverse("content:exam_subject_list", args=[category.slug, subject.slug])
        self.assertNotContains(self.client.get(subject_url), "Secret demo draft")
        self.assertEqual(self.client.get(reverse("content:category_list", args=["missing-exam"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("content:exam_subject_list", args=[category.slug, "missing-subject"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("content:previous_paper_detail", args=[
            category.slug, subject.slug, draft.slug,
        ])).status_code, 404)
        self.assertEqual(self.client.get(reverse("content:previous_paper_detail", args=[
            category.slug, subject.slug, "missing-paper",
        ])).status_code, 404)

    def test_legacy_exam_stage_archive_route_still_works(self):
        """The existing exam/stage URL continues to list its published resources."""
        category = ExamCategory.objects.get(slug="wbcs")
        stage = ExamStage.objects.create(category=category, name="Prelims", slug="prelims")
        page = ContentPage.objects.create(
            title="Legacy stage archive resource", slug="legacy-stage-resource", body="Visible",
            is_published=True, published_at=timezone.now(),
        )
        ResourceMetadata.objects.create(page=page, category=category, stage=stage, year=2024)

        response = self.client.get(reverse("content:stage_list", args=[category.slug, stage.slug]))
        self.assertContains(response, "Legacy stage archive resource")
