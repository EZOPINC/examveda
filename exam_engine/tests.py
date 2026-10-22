"""Verify exam authoring, owner isolation and the server-timed attempt lifecycle."""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from content.models import Subject

from .models import AttemptResponse, MockTest, MockTestQuestion, MockTestTranslation, Question, QuestionOption, QuestionOptionTranslation, QuestionTranslation, TestAttempt
from .services import TestUnavailable, available_test_languages, change_attempt_language, save_answer, start_test, submit_attempt, test_language_content


class ExamEngineWorkflowTests(TestCase):
    """Exercise student flows against a realistic single-choice test fixture."""

    @classmethod
    def setUpTestData(cls):
        """Create two students, a published test and three scored questions."""
        cls.student = get_user_model().objects.create_user(username="exam-student", password="test-password")
        cls.other_student = get_user_model().objects.create_user(username="another-student", password="test-password")
        subject = Subject.objects.create(name="History", slug="exam-history")
        cls.questions = []
        for index in range(1, 4):
            question = Question.objects.create(subject=subject, prompt=f"Question {index}?", explanation=f"Explanation {index}.", is_published=False)
            cls.questions.append(question)
            QuestionOption.objects.create(question=question, text=f"Question {index} correct", position=1, is_correct=True)
            QuestionOption.objects.create(question=question, text=f"Question {index} incorrect", position=2, is_correct=False)
            question.is_published = True
            question.save()
        cls.mock_test = MockTest.objects.create(
            title="WBCS practice", slug="wbcs-practice", description="Practice questions.", language="en", duration_minutes=5, is_published=True
        )
        cls.test_questions = []
        for index, question in enumerate(cls.questions, start=1):
            cls.test_questions.append(MockTestQuestion.objects.create(
                mock_test=cls.mock_test,
                question=question,
                position=index,
                marks=Decimal("2.00"),
                negative_marks=Decimal("0.50"),
            ))

    def start_for(self, user=None, now=None, language_code="en"):
        """Create an attempt through the approved transactional start service."""
        return start_test(user or self.student, self.mock_test.slug, language_code=language_code, now=now)

    def add_test_translation(self, language_code="hi", complete=True):
        """Create translated metadata, question prompts, and stable option labels."""
        MockTestTranslation.objects.create(
            mock_test=self.mock_test,
            language_code=language_code,
            title="डब्ल्यूबीसीएस अभ्यास" if language_code == "hi" else "ডব্লিউবিসিএস অনুশীলন",
            description="अभ्यास प्रश्न।" if language_code == "hi" else "অনুশীলনের প্রশ্ন।",
            is_published=True,
        )
        for question_index, question in enumerate(self.questions, start=1):
            translation = QuestionTranslation.objects.create(
                question=question,
                language_code=language_code,
                prompt=(f"प्रश्न {question_index}?" if language_code == "hi" else f"প্রশ্ন {question_index}?"),
                explanation=(f"व्याख्या {question_index}." if language_code == "hi" else f"ব্যাখ্যা {question_index}."),
                is_published=True,
            )
            options = list(question.options.order_by("position"))
            for option_index, option in enumerate(options, start=1):
                if complete or not (question_index == 1 and option_index == 2):
                    label = (f"विकल्प {option_index}" if language_code == "hi" else f"বিকল্প {option_index}")
                    QuestionOptionTranslation.objects.create(question_translation=translation, option=option, text=label)

    def test_language_translation_is_complete_and_preserves_shared_option_key(self):
        """Hindi variants render localized text while correctness stays on source option rows."""
        self.add_test_translation("hi")
        available = dict(available_test_languages(self.mock_test))
        self.assertIn("hi", available)
        attempt = self.start_for(language_code="hi")
        self.assertEqual(attempt.language_code, "hi")
        localized = test_language_content(self.mock_test, "hi")
        source_question = self.questions[0]
        correct_source_option = source_question.options.get(is_correct=True)
        localized_options = dict(localized["questions"][0]["options"])
        self.assertEqual(localized_options[correct_source_option], "विकल्प 1")
        self.assertEqual(sum(option.is_correct for option, _label in localized["questions"][0]["options"]), 1)

    def test_incomplete_translation_cannot_be_advertised_or_started(self):
        """Missing translated option text fails closed without falling back to English."""
        self.add_test_translation("hi", complete=False)
        self.assertNotIn("hi", dict(available_test_languages(self.mock_test)))
        with self.assertRaises(TestUnavailable):
            self.start_for(language_code="hi")

    def test_language_switch_preserves_attempt_timer_and_saved_answer(self):
        """Changing only the presentation language retains identity, timing, answer and key."""
        self.add_test_translation("hi")
        attempt = self.start_for()
        started_at, expires_at = attempt.started_at, attempt.expires_at
        selected = self.questions[0].options.get(is_correct=True)
        save_answer(self.student, attempt.pk, self.test_questions[0].pk, selected.pk)
        self.assertTrue(change_attempt_language(self.student, attempt.pk, "hi"))
        attempt.refresh_from_db()
        self.assertEqual(attempt.language_code, "hi")
        self.assertEqual((attempt.started_at, attempt.expires_at), (started_at, expires_at))
        self.assertEqual(attempt.responses.get(mock_test_question=self.test_questions[0]).selected_option_id, selected.pk)
        self.assertTrue(selected.is_correct)
        finalized = submit_attempt(self.student, attempt.pk)
        self.assertEqual(finalized.score, Decimal("2.00"))

    def test_active_attempt_cannot_switch_to_unpublished_language(self):
        """An existing attempt keeps its locale, while switching requires current publication."""
        self.add_test_translation("hi")
        attempt = self.start_for(language_code="en")
        localized_test = self.mock_test.translations.get(language_code="hi")
        localized_test.is_published = False
        localized_test.save()
        with self.assertRaises(ValidationError):
            change_attempt_language(self.student, attempt.pk, "hi")
        attempt.refresh_from_db()
        self.assertEqual(attempt.language_code, "en")

    def test_existing_attempt_keeps_its_language_after_locale_is_closed(self):
        """Unpublishing a locale stops new selection but does not strand its active attempt."""
        self.add_test_translation("hi")
        attempt = self.start_for(language_code="hi")
        localized_test = self.mock_test.translations.get(language_code="hi")
        localized_test.is_published = False
        localized_test.save()
        self.client.force_login(self.student)
        response = self.client.get(reverse("exam_engine:attempt_detail", args=[attempt.pk]))
        self.assertContains(response, "डब्ल्यूबीसीएस अभ्यास")
        self.assertContains(response, "प्रश्न 1?")

    def test_active_attempt_can_switch_language_after_test_closes_to_new_starts(self):
        """Closing a test to new students does not disable complete locales for active attempts."""
        self.add_test_translation("hi")
        attempt = self.start_for(language_code="en")
        self.mock_test.is_published = False
        self.mock_test.save()
        self.assertTrue(change_attempt_language(self.student, attempt.pk, "hi"))
        attempt.refresh_from_db()
        self.assertEqual(attempt.language_code, "hi")
        self.assertEqual(available_test_languages(self.mock_test), [])
        available_codes = [
            code for code, _label in available_test_languages(
                self.mock_test, allow_test_closed=True
            )
        ]
        self.assertEqual(available_codes, ["en", "hi"])

    def test_translated_question_must_include_explanation_when_source_has_one(self):
        """A localized test is unavailable when authored source explanations are omitted."""
        self.add_test_translation("hi")
        translation = self.questions[0].translations.get(language_code="hi")
        translation.explanation = ""
        translation.save()
        self.assertNotIn("hi", dict(available_test_languages(self.mock_test)))

    def test_mock_test_translation_needs_published_metadata_for_availability(self):
        """A question set alone cannot advertise a test without its translated title."""
        self.add_test_translation("hi")
        test_translation = self.mock_test.translations.get(language_code="hi")
        test_translation.is_published = False
        test_translation.save()
        self.assertNotIn("hi", dict(available_test_languages(self.mock_test)))

    def test_student_can_select_language_before_start_and_switch_over_http(self):
        """Public language choice and active language changes use the same attempt."""
        self.add_test_translation("hi")
        self.client.force_login(self.student)
        detail_url = reverse("exam_engine:mock_test_detail", args=[self.mock_test.slug])
        self.assertContains(self.client.get(detail_url), 'name="language_code" value="en"')
        start = self.client.post(reverse("exam_engine:start_test", args=[self.mock_test.slug]), {"language_code": "en"})
        attempt = TestAttempt.objects.get(user=self.student, mock_test=self.mock_test)
        selected = self.questions[0].options.get(is_correct=True)
        save_answer(self.student, attempt.pk, self.test_questions[0].pk, selected.pk)
        change = self.client.post(reverse("exam_engine:change_test_language", args=[attempt.pk]), {"language_code": "hi"})
        attempt.refresh_from_db()
        self.assertRedirects(start, reverse("exam_engine:attempt_detail", args=[attempt.pk]))
        self.assertRedirects(change, reverse("exam_engine:attempt_detail", args=[attempt.pk]))
        self.assertEqual(attempt.language_code, "hi")
        self.assertEqual(attempt.responses.get(mock_test_question=self.test_questions[0]).selected_option_id, selected.pk)
        self.assertContains(self.client.get(change.url), "प्रश्न 1?")

    def test_incomplete_question_language_never_falls_back_to_source_language(self):
        """A test with even one untranslated prompt is hidden in that language."""
        self.add_test_translation("hi")
        self.questions[1].translations.get(language_code="hi").delete()
        self.assertNotIn("hi", dict(available_test_languages(self.mock_test)))

    def test_published_translation_cannot_bypass_unpublished_source_question(self):
        """A translated variant remains unavailable while its logical source question is draft."""
        self.add_test_translation("hi")
        question = self.questions[0]
        question.is_published = False
        question.save()
        self.assertNotIn("hi", dict(available_test_languages(self.mock_test)))

    def test_global_language_switch_localizes_shared_ui(self):
        """The standard Django language endpoint changes interface copy without changing content records."""
        home = reverse("home")
        localized_labels = {
            "hi": ("निःशुल्क अध्ययन सामग्री", 'lang="hi"'),
            "bn": ("বিনামূল্যে পড়ার উপকরণ", 'lang="bn"'),
        }
        for language_code, (label, html_language) in localized_labels.items():
            self.client.post(reverse("set_language"), {"language": language_code, "next": home})
            response = self.client.get(home)
            self.assertContains(response, label)
            self.assertContains(response, html_language)

    def test_bengali_mock_exam_uses_one_rendered_language(self):
        """Bengali prompt/options and document language render without source-language text."""
        self.add_test_translation("bn")
        self.client.force_login(self.student)
        attempt = self.start_for(language_code="bn")
        response = self.client.get(reverse("exam_engine:attempt_detail", args=[attempt.pk]))
        self.assertContains(response, "ডব্লিউবিসিএস অনুশীলন")
        self.assertContains(response, "প্রশ্ন 1?")
        self.assertContains(response, "বিকল্প 1")
        self.assertContains(response, 'lang="bn"')
        self.assertNotContains(response, "Question 1?")

    def test_staff_can_open_question_and_test_translation_editors(self):
        """Admin translation forms expose localized preview and test metadata in place."""
        self.add_test_translation("hi")
        staff = get_user_model().objects.create_superuser(username="translation-admin", password="test-password", email="translation-admin@example.test")
        self.client.force_login(staff)
        question_translation = self.questions[0].translations.get(language_code="hi")
        question_admin = self.client.get(reverse("admin:exam_engine_questiontranslation_change", args=[question_translation.pk]))
        test_admin = self.client.get(reverse("admin:exam_engine_mocktest_change", args=[self.mock_test.pk]))
        self.assertEqual(question_admin.status_code, 200)
        self.assertContains(question_admin, "Translation completeness")
        self.assertContains(question_admin, "विकल्प 1")
        self.assertEqual(test_admin.status_code, 200)
        self.assertContains(test_admin, "डब्ल्यूबीसीएस अभ्यास")

    def test_admin_cannot_publish_translation_with_missing_option_label(self):
        """The admin formset checks submitted publication state, not only saved state."""
        translation = QuestionTranslation.objects.create(
            question=self.questions[0], language_code="hi", prompt="प्रश्न?", is_published=False
        )
        first_option = self.questions[0].options.order_by("position").first()
        localized_option = QuestionOptionTranslation.objects.create(
            question_translation=translation, option=first_option, text="विकल्प"
        )
        staff = get_user_model().objects.create_superuser(username="translation-publish-admin", password="test-password", email="publish-admin@example.test")
        self.client.force_login(staff)
        change_url = reverse("admin:exam_engine_questiontranslation_change", args=[translation.pk])
        page = self.client.get(change_url)
        prefix = page.context["inline_admin_formsets"][0].formset.prefix
        payload = {
            "question": self.questions[0].pk,
            "language_code": "hi",
            "prompt": "प्रश्न?",
            "explanation": "",
            "is_published": "on",
            "id": translation.pk,
            "_save": "Save",
            f"{prefix}-TOTAL_FORMS": "1",
            f"{prefix}-INITIAL_FORMS": "1",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
            f"{prefix}-0-id": localized_option.pk,
            f"{prefix}-0-option": first_option.pk,
            f"{prefix}-0-text": "विकल्प",
        }
        response = self.client.post(change_url, payload)
        translation.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(translation.is_published)
        self.assertContains(response, "Every answer option needs translated text")

    def test_admin_translation_content_is_read_only_after_first_attempt(self):
        """Admin continues to show historical translation previews without offering text edits."""
        self.add_test_translation("hi")
        self.start_for()
        staff = get_user_model().objects.create_superuser(username="frozen-translation-admin", password="test-password", email="frozen-admin@example.test")
        self.client.force_login(staff)
        question_translation = self.questions[0].translations.get(language_code="hi")
        question_admin = self.client.get(reverse("admin:exam_engine_questiontranslation_change", args=[question_translation.pk]))
        test_admin = self.client.get(reverse("admin:exam_engine_mocktest_change", args=[self.mock_test.pk]))
        self.assertEqual(question_admin.status_code, 200)
        self.assertEqual(test_admin.status_code, 200)
        self.assertContains(question_admin, "प्रश्न 1?")
        self.assertContains(test_admin, "डब्ल्यूबीसीएस अभ्यास")

    def test_missing_language_choice_is_rejected_for_a_new_attempt(self):
        """A new attempt must carry an explicit language supported by the complete test."""
        with self.assertRaises(TestUnavailable):
            start_test(self.student, self.mock_test.slug)
        with self.assertRaises(TestUnavailable):
            self.start_for(language_code="fr")

    def test_legacy_test_requires_explicit_source_language_assignment(self):
        """A translation row cannot silently activate a legacy test with unknown source language."""
        self.add_test_translation("hi")
        self.mock_test.language = None
        self.mock_test.save()
        self.assertEqual(available_test_languages(self.mock_test), [])
        with self.assertRaises(TestUnavailable):
            self.start_for(language_code="hi")

    def test_legacy_attempt_without_locale_keeps_source_text(self):
        """Old attempts with a null language remain renderable without guessing a test locale."""
        attempt = self.start_for()
        attempt.language_code = None
        attempt.save(update_fields=["language_code"])
        self.client.force_login(self.student)
        response = self.client.get(reverse("exam_engine:attempt_detail", args=[attempt.pk]))
        self.assertContains(response, "WBCS practice")
        self.assertContains(response, "Question 1?")

    def test_active_exam_response_uses_attempt_language_and_hides_answer_key(self):
        """The active page renders one complete chosen locale and no correctness metadata."""
        self.add_test_translation("hi")
        self.client.force_login(self.student)
        attempt = self.start_for(language_code="hi")
        response = self.client.get(reverse("exam_engine:attempt_detail", args=[attempt.pk]))
        self.assertContains(response, "डब्ल्यूबीसीएस अभ्यास")
        self.assertContains(response, "प्रश्न 1?")
        self.assertContains(response, "विकल्प 1")
        self.assertNotContains(response, "Explanation 1.")
        self.assertNotContains(response, "Correct answer:")

    def test_start_records_server_times_and_reuses_active_attempt(self):
        """Repeated starts resume the same active attempt without extending time."""
        started_at = timezone.now()
        attempt = self.start_for(now=started_at)
        resumed = self.start_for(now=started_at + timedelta(minutes=1))
        self.assertEqual(resumed.pk, attempt.pk)
        self.assertEqual(attempt.started_at, started_at)
        self.assertEqual(attempt.expires_at, started_at + timedelta(minutes=5))
        self.assertEqual(TestAttempt.objects.filter(user=self.student, mock_test=self.mock_test).count(), 1)

    def test_authenticated_start_endpoint_creates_attempt(self):
        """The student HTTP action delegates creation to the server service."""
        self.client.force_login(self.student)
        response = self.client.post(reverse("exam_engine:start_test", args=[self.mock_test.slug]), {"language_code": "en"})
        attempt = TestAttempt.objects.get(user=self.student, mock_test=self.mock_test)
        self.assertRedirects(response, reverse("exam_engine:attempt_detail", args=[attempt.pk]))
        self.assertEqual(attempt.state, TestAttempt.State.IN_PROGRESS)

    def test_student_completes_exam_workflow_over_http(self):
        """A student can start, view, save, submit and review one attempt."""
        self.client.force_login(self.student)
        start_response = self.client.post(reverse("exam_engine:start_test", args=[self.mock_test.slug]), {"language_code": "en"})
        attempt = TestAttempt.objects.get(user=self.student, mock_test=self.mock_test)
        self.assertRedirects(start_response, reverse("exam_engine:attempt_detail", args=[attempt.pk]))

        exam_response = self.client.get(start_response.url)
        self.assertContains(exam_response, "Question 1?")
        self.assertNotContains(exam_response, "Explanation 1.")
        self.assertContains(exam_response, 'name="robots" content="noindex, nofollow"')
        save_response = self.client.post(reverse("exam_engine:save_answer", args=[attempt.pk]), {
            "mock_test_question_id": self.test_questions[0].pk,
            "selected_option_id": self.questions[0].options.get(is_correct=True).pk,
        })
        self.assertEqual(save_response.status_code, 200)
        self.assertTrue(save_response.json()["saved"])

        submit_response = self.client.post(reverse("exam_engine:submit_attempt", args=[attempt.pk]))
        self.assertRedirects(submit_response, reverse("exam_engine:attempt_detail", args=[attempt.pk]))
        result_response = self.client.get(submit_response.url)
        self.assertContains(result_response, "Score")
        self.assertContains(result_response, "2.00")
        self.assertContains(result_response, "Explanation 1.")
        self.assertContains(result_response, 'name="robots" content="noindex, nofollow"')

    def test_active_attempt_resumes_after_test_is_closed_for_new_starts(self):
        """Closing availability stops new attempts without stranding a student."""
        attempt = self.start_for()
        self.mock_test.is_published = False
        self.mock_test.save()
        self.assertEqual(self.start_for().pk, attempt.pk)
        submit_attempt(self.student, attempt.pk)
        with self.assertRaises(TestUnavailable):
            self.start_for()

    def test_unauthenticated_start_redirects_to_login_without_creating_attempt(self):
        """The public test page is visible but starting needs authentication."""
        response = self.client.get(reverse("exam_engine:mock_test_detail", args=[self.mock_test.slug]))
        self.assertContains(response, self.mock_test.title)
        start_response = self.client.post(reverse("exam_engine:start_test", args=[self.mock_test.slug]), {"language_code": "en"})
        self.assertRedirects(start_response, f"/accounts/login/?next=/mock-tests/{self.mock_test.slug}/")
        self.assertEqual(self.client.get(start_response.url).status_code, 200)
        self.assertFalse(TestAttempt.objects.exists())

    def test_saving_answer_is_idempotent_and_restores_selected_option(self):
        """Repeated autosaves update a single response, rendered on resumption."""
        attempt = self.start_for()
        correct_option = self.questions[0].options.get(is_correct=True)
        save_answer(self.student, attempt.pk, self.test_questions[0].pk, correct_option.pk)
        save_answer(self.student, attempt.pk, self.test_questions[0].pk, correct_option.pk)
        self.assertEqual(AttemptResponse.objects.filter(attempt=attempt, mock_test_question=self.test_questions[0]).count(), 1)
        self.client.force_login(self.student)
        response = self.client.get(reverse("exam_engine:attempt_detail", args=[attempt.pk]))
        self.assertContains(response, 'checked')
        self.assertNotContains(response, "Explanation 1.")
        self.assertNotContains(response, "Correct answer:")

    def test_csrf_is_required_for_answer_saves(self):
        """State-changing autosave requests require Django's CSRF token."""
        attempt = self.start_for()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student)
        client.get(reverse("exam_engine:attempt_detail", args=[attempt.pk]))
        payload = {
            "mock_test_question_id": self.test_questions[0].pk,
            "selected_option_id": self.questions[0].options.get(is_correct=True).pk,
        }
        save_url = reverse("exam_engine:save_answer", args=[attempt.pk])
        self.assertEqual(client.post(save_url, payload).status_code, 403)
        csrf_token = client.cookies["csrftoken"].value
        self.assertEqual(client.post(save_url, payload, HTTP_X_CSRFTOKEN=csrf_token).status_code, 200)

    def test_students_cannot_read_or_change_another_users_attempt(self):
        """Attempt IDs never replace the server-side user ownership check."""
        attempt = self.start_for()
        self.client.force_login(self.other_student)
        self.assertEqual(self.client.get(reverse("exam_engine:attempt_detail", args=[attempt.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("exam_engine:submit_attempt", args=[attempt.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("exam_engine:change_test_language", args=[attempt.pk]), {"language_code": "en"}).status_code, 404)
        self.assertEqual(self.client.post(reverse("exam_engine:save_answer", args=[attempt.pk]), {
            "mock_test_question_id": self.test_questions[0].pk,
            "selected_option_id": self.questions[0].options.get(is_correct=True).pk,
        }).status_code, 404)

    def test_scoring_uses_server_rules_and_submission_retry_keeps_one_result(self):
        """Correct, incorrect, and unanswered counts and marks are calculated once."""
        attempt = self.start_for()
        correct = self.questions[0].options.get(is_correct=True)
        incorrect = self.questions[1].options.get(is_correct=False)
        save_answer(self.student, attempt.pk, self.test_questions[0].pk, correct.pk)
        save_answer(self.student, attempt.pk, self.test_questions[1].pk, incorrect.pk)
        first_result = submit_attempt(self.student, attempt.pk)
        repeated_result = submit_attempt(self.student, attempt.pk)
        self.assertEqual(first_result.pk, repeated_result.pk)
        self.assertEqual(first_result.state, TestAttempt.State.SUBMITTED)
        self.assertEqual(first_result.score, Decimal("1.50"))
        self.assertEqual(first_result.correct_count, 1)
        self.assertEqual(first_result.incorrect_count, 1)
        self.assertEqual(first_result.unanswered_count, 1)
        self.assertEqual(TestAttempt.objects.filter(user=self.student, mock_test=self.mock_test).count(), 1)
        self.assertEqual(AttemptResponse.objects.filter(attempt=attempt).count(), 2)

    def test_answer_key_and_explanation_are_revealed_only_after_finalization(self):
        """Active exam HTML excludes answer review; the owner sees it after submit."""
        attempt = self.start_for()
        self.client.force_login(self.student)
        active_html = self.client.get(reverse("exam_engine:attempt_detail", args=[attempt.pk])).content.decode()
        self.assertNotIn("Explanation 1.", active_html)
        self.assertNotIn("Correct answer:", active_html)
        submit_attempt(self.student, attempt.pk)
        result_html = self.client.get(reverse("exam_engine:attempt_detail", args=[attempt.pk])).content.decode()
        self.assertIn("Explanation 1.", result_html)
        self.assertIn("Correct answer:", result_html)

    def test_exact_deadline_expires_attempt_and_scores_saved_answers(self):
        """At now equal to the server deadline, saves are rejected and answers finalized."""
        started_at = timezone.now()
        attempt = self.start_for(now=started_at)
        correct = self.questions[0].options.get(is_correct=True)
        save_answer(self.student, attempt.pk, self.test_questions[0].pk, correct.pk, now=started_at + timedelta(seconds=10))
        outcome = save_answer(self.student, attempt.pk, self.test_questions[1].pk, correct.pk, now=attempt.expires_at)
        attempt.refresh_from_db()
        self.assertFalse(outcome.was_saved)
        self.assertEqual(attempt.state, TestAttempt.State.EXPIRED)
        self.assertEqual(attempt.score, Decimal("2.00"))
        self.assertEqual(attempt.correct_count, 1)
        self.assertEqual(attempt.unanswered_count, 2)
        self.assertIsNone(attempt.submitted_at)
        self.assertIsNotNone(attempt.finalized_at)
        self.assertEqual(AttemptResponse.objects.filter(attempt=attempt).count(), 1)

    def test_submit_at_deadline_expires_instead_of_marking_submitted(self):
        """A late submit request cannot claim on-time completion."""
        attempt = self.start_for()
        expired = submit_attempt(self.student, attempt.pk, now=attempt.expires_at)
        self.assertEqual(expired.state, TestAttempt.State.EXPIRED)
        self.assertIsNone(expired.submitted_at)

    def test_interrupted_attempt_resumes_then_later_start_creates_new_attempt(self):
        """Resume preserves the original deadline; a terminal attempt can be retaken."""
        attempt = self.start_for()
        resumed = self.start_for(now=attempt.started_at + timedelta(minutes=2))
        self.assertEqual(resumed.pk, attempt.pk)
        self.assertEqual(resumed.expires_at, attempt.expires_at)
        submit_attempt(self.student, attempt.pk)
        later = self.start_for(now=attempt.started_at + timedelta(minutes=3))
        self.assertNotEqual(later.pk, attempt.pk)

    def test_expired_attempt_is_finalized_when_owner_reopens_exam(self):
        """A stale in-progress row is transitioned before rendering a result."""
        attempt = self.start_for()
        self.client.force_login(self.student)
        with patch("exam_engine.services.timezone.now", return_value=attempt.expires_at):
            response = self.client.get(reverse("exam_engine:attempt_detail", args=[attempt.pk]))
        attempt.refresh_from_db()
        self.assertEqual(attempt.state, TestAttempt.State.EXPIRED)
        self.assertContains(response, "Answer review")

    def test_invalid_option_and_question_membership_are_rejected(self):
        """A response cannot select another question's option or another test item."""
        attempt = self.start_for()
        other_option = self.questions[1].options.get(is_correct=True)
        with self.assertRaises(ValidationError):
            save_answer(self.student, attempt.pk, self.test_questions[0].pk, other_option.pk)
        with self.assertRaises(ValidationError):
            save_answer(self.student, attempt.pk, self.test_questions[0].pk + 10000, other_option.pk)

    def test_terminal_attempt_cannot_be_modified(self):
        """Submissions lock answer writes even when the same owner retries."""
        attempt = self.start_for()
        submit_attempt(self.student, attempt.pk)
        result = save_answer(self.student, attempt.pk, self.test_questions[0].pk, self.questions[0].options.get(is_correct=True).pk)
        self.assertFalse(result.was_saved)
        self.assertFalse(AttemptResponse.objects.filter(attempt=attempt).exists())

    def test_answer_database_error_does_not_leave_a_partial_response(self):
        """A failed answer write rolls back its transaction and keeps the attempt active."""
        attempt = self.start_for()
        correct_option = self.questions[0].options.get(is_correct=True)
        with patch.object(AttemptResponse.objects, "update_or_create", side_effect=DatabaseError("simulated write failure")):
            with self.assertRaises(DatabaseError):
                save_answer(self.student, attempt.pk, self.test_questions[0].pk, correct_option.pk)

        attempt.refresh_from_db()
        self.assertEqual(attempt.state, TestAttempt.State.IN_PROGRESS)
        self.assertFalse(AttemptResponse.objects.filter(attempt=attempt).exists())

    def test_submission_database_error_does_not_leave_a_partial_result(self):
        """A failed score/finalization transaction keeps terminal fields unchanged."""
        attempt = self.start_for()
        with patch("exam_engine.services.calculate_attempt_result", side_effect=DatabaseError("simulated score failure")):
            with self.assertRaises(DatabaseError):
                submit_attempt(self.student, attempt.pk)

        attempt.refresh_from_db()
        self.assertEqual(attempt.state, TestAttempt.State.IN_PROGRESS)
        self.assertIsNone(attempt.finalized_at)
        self.assertIsNone(attempt.submitted_at)

    def test_started_test_and_question_graph_cannot_be_edited(self):
        """The immutable graph keeps saved result interpretation stable."""
        attempt = self.start_for()
        question = self.questions[0]
        question.prompt = "Changed after start"
        with self.assertRaises(ValidationError):
            question.save()
        option = question.options.get(is_correct=True)
        option.text = "Changed key"
        with self.assertRaises(ValidationError):
            option.save()
        mock_test = self.mock_test
        mock_test.title = "Changed test"
        with self.assertRaises(ValidationError):
            mock_test.save()
        test_question = self.test_questions[0]
        test_question.marks = Decimal("3.00")
        with self.assertRaises(ValidationError):
            test_question.save()
        self.assertEqual(attempt.state, TestAttempt.State.IN_PROGRESS)


class ExamAuthoringValidationTests(TestCase):
    """Verify unpublished and invalid question sets cannot enter student attempts."""

    def test_unpublished_test_cannot_be_started(self):
        """Only a published test is eligible for an attempt."""
        student = get_user_model().objects.create_user(username="authoring-test-student", password="test-password")
        mock_test = MockTest.objects.create(title="Draft", slug="draft-mock", duration_minutes=20, is_published=False)
        client = Client()
        client.force_login(student)
        self.assertEqual(client.post(reverse("exam_engine:start_test", args=[mock_test.slug]), {"language_code": "en"}).status_code, 404)
