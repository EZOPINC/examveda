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

from .models import AttemptResponse, MockTest, MockTestQuestion, Question, QuestionOption, TestAttempt
from .services import TestUnavailable, save_answer, start_test, submit_attempt


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
            title="WBCS practice", slug="wbcs-practice", description="Practice questions.", duration_minutes=5, is_published=True
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

    def start_for(self, user=None, now=None):
        """Create an attempt through the approved transactional start service."""
        return start_test(user or self.student, self.mock_test.slug, now=now)

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
        response = self.client.post(reverse("exam_engine:start_test", args=[self.mock_test.slug]))
        attempt = TestAttempt.objects.get(user=self.student, mock_test=self.mock_test)
        self.assertRedirects(response, reverse("exam_engine:attempt_detail", args=[attempt.pk]))
        self.assertEqual(attempt.state, TestAttempt.State.IN_PROGRESS)

    def test_student_completes_exam_workflow_over_http(self):
        """A student can start, view, save, submit and review one attempt."""
        self.client.force_login(self.student)
        start_response = self.client.post(reverse("exam_engine:start_test", args=[self.mock_test.slug]))
        attempt = TestAttempt.objects.get(user=self.student, mock_test=self.mock_test)
        self.assertRedirects(start_response, reverse("exam_engine:attempt_detail", args=[attempt.pk]))

        exam_response = self.client.get(start_response.url)
        self.assertContains(exam_response, "Question 1?")
        self.assertNotContains(exam_response, "Explanation 1.")
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
        start_response = self.client.post(reverse("exam_engine:start_test", args=[self.mock_test.slug]))
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
        self.assertEqual(client.post(reverse("exam_engine:start_test", args=[mock_test.slug])).status_code, 404)
