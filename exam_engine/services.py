"""Run transactional exam start, answer-save, expiry, and scoring operations.

Views call these functions instead of deciding attempt state themselves. Row
locks serialize student requests and PostgreSQL constraints backstop invariants.
All time decisions use server timestamps passed into the service for testability.
"""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from access_control.services import user_can_access

from .models import AttemptResponse, MockTest, MockTestQuestion, QuestionOption, TestAttempt


class TestUnavailable(Exception):
    """Indicate that a test cannot currently be started by a student."""


@dataclass(frozen=True)
class AnswerSaveResult:
    """Describe whether a response was saved or the attempt had expired."""

    attempt: TestAttempt
    was_saved: bool


def _test_is_available(mock_test, now):
    """Return whether the published test is within its configured start window."""
    if not mock_test.is_published:
        return False
    if mock_test.available_from and now < mock_test.available_from:
        return False
    if mock_test.available_until and now >= mock_test.available_until:
        return False
    return True


def _validate_test_question_set(mock_test):
    """Reject empty or invalid test compositions before creating an attempt."""
    test_questions = list(
        MockTestQuestion.objects.filter(mock_test=mock_test)
        .select_related("question")
        .prefetch_related("question__options")
        .order_by("position")
    )
    if not test_questions:
        raise TestUnavailable("This test does not have any questions yet.")
    for test_question in test_questions:
        options = list(test_question.question.options.all())
        if not test_question.question.is_published or len(options) < 2 or sum(option.is_correct for option in options) != 1:
            raise TestUnavailable("This test is not ready to start.")
    return test_questions


def calculate_attempt_result(attempt):
    """Compute authoritative marks and response totals from stored responses."""
    test_questions = list(attempt.mock_test.test_questions.order_by("position"))
    responses = {
        response.mock_test_question_id: response
        for response in attempt.responses.select_related("selected_option").all()
    }
    score = Decimal("0.00")
    correct_count = 0
    incorrect_count = 0
    unanswered_count = 0
    for test_question in test_questions:
        response = responses.get(test_question.pk)
        selected_option = response.selected_option if response else None
        if selected_option is None:
            unanswered_count += 1
        elif selected_option.question_id != test_question.question_id:
            raise ValidationError("A response contains an option from another question.")
        elif selected_option.is_correct:
            correct_count += 1
            score += test_question.marks
        else:
            incorrect_count += 1
            score -= test_question.negative_marks
    return {
        "score": score,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "unanswered_count": unanswered_count,
    }


def _finalize_attempt(attempt, state, finalized_at):
    """Write terminal state and its score summary in the caller's transaction."""
    if attempt.state != TestAttempt.State.IN_PROGRESS:
        return attempt
    result = calculate_attempt_result(attempt)
    attempt.state = state
    attempt.finalized_at = finalized_at
    attempt.submitted_at = finalized_at if state == TestAttempt.State.SUBMITTED else None
    for field_name, value in result.items():
        setattr(attempt, field_name, value)
    attempt.save(update_fields=["state", "finalized_at", "submitted_at", "score", "correct_count", "incorrect_count", "unanswered_count"])
    return attempt


@transaction.atomic
def start_test(user, test_slug, now=None):
    """Resume the user's active attempt or start a valid published test."""
    now = now or timezone.now()
    try:
        mock_test = MockTest.objects.select_for_update().get(slug=test_slug)
    except MockTest.DoesNotExist as error:
        raise TestUnavailable("This test is not available.") from error
    active_attempt = TestAttempt.objects.select_for_update().filter(
        user=user, mock_test=mock_test, state=TestAttempt.State.IN_PROGRESS
    ).first()
    if active_attempt:
        if now >= active_attempt.expires_at:
            _finalize_attempt(active_attempt, TestAttempt.State.EXPIRED, now)
            if not _test_is_available(mock_test, now):
                return active_attempt
        else:
            return active_attempt

    if not _test_is_available(mock_test, now):
        raise TestUnavailable("This test is not available at this time.")
    if not user_can_access(user, is_published=mock_test.is_published, is_public=True):
        raise TestUnavailable("This test is not available to this account.")

    _validate_test_question_set(mock_test)
    return TestAttempt.objects.create(
        user=user,
        mock_test=mock_test,
        state=TestAttempt.State.IN_PROGRESS,
        started_at=now,
        expires_at=now + timedelta(minutes=mock_test.duration_minutes),
    )


@transaction.atomic
def load_attempt(user, attempt_id, now=None):
    """Return only an owned attempt and finalize it if its deadline passed."""
    now = now or timezone.now()
    attempt = TestAttempt.objects.select_for_update().select_related("mock_test").get(pk=attempt_id, user=user)
    if attempt.state == TestAttempt.State.IN_PROGRESS and now >= attempt.expires_at:
        _finalize_attempt(attempt, TestAttempt.State.EXPIRED, now)
    return attempt


@transaction.atomic
def finalize_expired_attempts(user, now=None):
    """Finalize expired attempts before showing the student's attempt history."""
    now = now or timezone.now()
    expired_attempts = list(
        TestAttempt.objects.select_for_update()
        .select_related("mock_test")
        .filter(user=user, state=TestAttempt.State.IN_PROGRESS, expires_at__lte=now)
        .order_by("pk")
    )
    for attempt in expired_attempts:
        _finalize_attempt(attempt, TestAttempt.State.EXPIRED, now)
    return len(expired_attempts)


@transaction.atomic
def save_answer(user, attempt_id, mock_test_question_id, selected_option_id, now=None):
    """Idempotently replace or clear one answer while the attempt is editable."""
    now = now or timezone.now()
    attempt = TestAttempt.objects.select_for_update().select_related("mock_test").get(pk=attempt_id, user=user)
    if attempt.state != TestAttempt.State.IN_PROGRESS:
        return AnswerSaveResult(attempt=attempt, was_saved=False)
    if now >= attempt.expires_at:
        _finalize_attempt(attempt, TestAttempt.State.EXPIRED, now)
        return AnswerSaveResult(attempt=attempt, was_saved=False)
    try:
        mock_test_question = MockTestQuestion.objects.get(pk=mock_test_question_id, mock_test=attempt.mock_test)
    except MockTestQuestion.DoesNotExist as error:
        raise ValidationError("Question does not belong to this attempt's test.") from error
    if selected_option_id in (None, ""):
        selected_option = None
    else:
        try:
            selected_option = QuestionOption.objects.get(pk=selected_option_id, question=mock_test_question.question)
        except (ValueError, TypeError, QuestionOption.DoesNotExist) as error:
            raise ValidationError("Selected answer is not an option for this question.") from error
    AttemptResponse.objects.update_or_create(
        attempt=attempt,
        mock_test_question=mock_test_question,
        defaults={"selected_option": selected_option},
    )
    return AnswerSaveResult(attempt=attempt, was_saved=True)


@transaction.atomic
def submit_attempt(user, attempt_id, now=None):
    """Finalize once, returning the same persisted result for retries."""
    now = now or timezone.now()
    attempt = TestAttempt.objects.select_for_update().select_related("mock_test").get(pk=attempt_id, user=user)
    if attempt.state != TestAttempt.State.IN_PROGRESS:
        return attempt
    if now >= attempt.expires_at:
        return _finalize_attempt(attempt, TestAttempt.State.EXPIRED, now)
    return _finalize_attempt(attempt, TestAttempt.State.SUBMITTED, now)
