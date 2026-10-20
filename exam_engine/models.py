"""Persist authored questions, tests and server-authoritative attempts.

Admin, exam views, and lifecycle services depend on these records. Once an
attempt starts, the relevant authored graph is frozen so history remains
correct without introducing separate version or snapshot tables.
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Q

from content.models import Subject, Topic


class Question(models.Model):
    """Represent one published single-choice exam question."""

    class Language(models.TextChoices):
        ENGLISH = "en", "English"
        BENGALI = "bn", "Bengali"

    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="questions")
    topic = models.ForeignKey(Topic, null=True, blank=True, on_delete=models.PROTECT, related_name="questions")
    prompt = models.TextField()
    explanation = models.TextField(blank=True)
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.ENGLISH)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["subject__name", "id"]
        indexes = [models.Index(fields=["is_published", "subject"], name="exam_question_public_idx")]

    def clean(self):
        """Ensure optional topic taxonomy belongs to the chosen subject."""
        super().clean()
        if self.topic_id and self.subject_id and self.topic.subject_id != self.subject_id:
            raise ValidationError({"topic": "Topic must belong to the selected subject."})

    def _has_started_attempt(self):
        """Return whether any frozen test graph contains this question."""
        return self.pk and TestAttempt.objects.filter(mock_test__test_questions__question_id=self.pk).exists()

    @transaction.atomic
    def save(self, *args, **kwargs):
        """Prevent edits that could rewrite a historical exam attempt."""
        if self.pk:
            test_ids = list(MockTestQuestion.objects.filter(question_id=self.pk).values_list("mock_test_id", flat=True).distinct())
            list(MockTest.objects.select_for_update().filter(pk__in=test_ids).order_by("pk"))
            if TestAttempt.objects.filter(mock_test_id__in=test_ids).exists():
                raise ValidationError("Questions used by a started test cannot be changed; create a new question.")
        super().save(*args, **kwargs)

    def __str__(self):
        """Return a short prompt label for staff forms."""
        return self.prompt[:80]


class QuestionOption(models.Model):
    """Represent one ordered answer option and its private correctness flag."""

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.TextField()
    position = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ["position", "id"]
        constraints = [models.UniqueConstraint(fields=["question", "position"], name="exam_option_question_position_uniq")]

    @transaction.atomic
    def save(self, *args, **kwargs):
        """Keep answer text and correctness stable after a test starts."""
        locked_question_ids = {self.question_id}
        if self.pk:
            old_question_id = type(self).objects.filter(pk=self.pk).values_list("question_id", flat=True).first()
            locked_question_ids.add(old_question_id)
        test_ids = list(MockTestQuestion.objects.filter(question_id__in=locked_question_ids).values_list("mock_test_id", flat=True).distinct())
        list(MockTest.objects.select_for_update().filter(pk__in=test_ids).order_by("pk"))
        if TestAttempt.objects.filter(mock_test_id__in=test_ids).exists():
            raise ValidationError("Options used by a started test cannot be changed; create a new question.")
        super().save(*args, **kwargs)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        """Prevent removing an option from a question in historical attempts."""
        test_ids = list(MockTestQuestion.objects.filter(question_id=self.question_id).values_list("mock_test_id", flat=True).distinct())
        list(MockTest.objects.select_for_update().filter(pk__in=test_ids).order_by("pk"))
        if TestAttempt.objects.filter(mock_test_id__in=test_ids).exists():
            raise ValidationError("Options used by a started test cannot be deleted.")
        return super().delete(*args, **kwargs)

    def __str__(self):
        """Return the option position and owning question label."""
        return f"Option {self.position}: {self.question}"


class MockTest(models.Model):
    """Define a published test's availability and time limit."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(240)])
    available_from = models.DateTimeField(null=True, blank=True)
    available_until = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_mock_tests")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        indexes = [models.Index(fields=["is_published", "available_from", "available_until"], name="exam_test_availability_idx")]

    def clean(self):
        """Require a forward availability interval when both bounds are set."""
        super().clean()
        if self.available_from and self.available_until and self.available_from >= self.available_until:
            raise ValidationError({"available_until": "Availability end must be after its start."})

    def _has_started_attempt(self):
        """Return whether any student has started this test."""
        return self.pk and self.attempts.exists()

    @transaction.atomic
    def save(self, *args, **kwargs):
        """Freeze historical test rules while allowing staff to close new starts."""
        if self.pk:
            original_test = type(self).objects.select_for_update().filter(pk=self.pk).first()
            if original_test and original_test._has_started_attempt():
                immutable_fields = ("title", "slug", "description", "duration_minutes")
                if any(getattr(original_test, field) != getattr(self, field) for field in immutable_fields):
                    raise ValidationError("Test details and duration cannot change after an attempt starts; create a new test.")
        super().save(*args, **kwargs)

    def __str__(self):
        """Return the test title."""
        return self.title


class MockTestQuestion(models.Model):
    """Join an ordered question to a test with its scoring values."""

    mock_test = models.ForeignKey(MockTest, on_delete=models.PROTECT, related_name="test_questions")
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="test_questions")
    position = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    marks = models.DecimalField(max_digits=7, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    negative_marks = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["mock_test", "position"], name="exam_test_question_position_uniq"),
            models.UniqueConstraint(fields=["mock_test", "question"], name="exam_test_question_pair_uniq"),
            models.CheckConstraint(condition=Q(marks__gt=0), name="exam_question_marks_positive"),
            models.CheckConstraint(condition=Q(negative_marks__gte=0), name="exam_negative_marks_nonnegative"),
            models.CheckConstraint(condition=Q(negative_marks__lte=models.F("marks")), name="exam_negative_marks_lte_marks"),
        ]

    def clean(self):
        """Require a published question with a complete single-choice key."""
        super().clean()
        if self.question_id:
            if not self.question.is_published:
                raise ValidationError({"question": "Only published questions can be added to a test."})
            option_totals = self.question.options.aggregate(total=models.Count("id"), correct=models.Count("id", filter=Q(is_correct=True)))
            if option_totals["total"] < 2 or option_totals["correct"] != 1:
                raise ValidationError({"question": "Question must have at least two options and exactly one correct option."})

    @transaction.atomic
    def save(self, *args, **kwargs):
        """Prevent changing test composition after attempts begin."""
        test_ids = {self.mock_test_id}
        if self.pk:
            old_test_id = type(self).objects.filter(pk=self.pk).values_list("mock_test_id", flat=True).first()
            test_ids.add(old_test_id)
        list(MockTest.objects.select_for_update().filter(pk__in=test_ids).order_by("pk"))
        if TestAttempt.objects.filter(mock_test_id__in=test_ids).exists():
            raise ValidationError("Questions in a test with attempts cannot be changed.")
        super().save(*args, **kwargs)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        """Prevent removing a question from a test with attempt history."""
        list(MockTest.objects.select_for_update().filter(pk=self.mock_test_id))
        if TestAttempt.objects.filter(mock_test_id=self.mock_test_id).exists():
            raise ValidationError("Questions in a test with attempts cannot be deleted.")
        return super().delete(*args, **kwargs)

    def __str__(self):
        """Return the ordered question's test label."""
        return f"{self.mock_test}: question {self.position}"


class TestAttempt(models.Model):
    """Record one student's server-timed attempt and final score summary."""

    class State(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        SUBMITTED = "submitted", "Submitted"
        EXPIRED = "expired", "Expired"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="mock_test_attempts")
    mock_test = models.ForeignKey(MockTest, on_delete=models.PROTECT, related_name="attempts")
    state = models.CharField(max_length=16, choices=State.choices, default=State.IN_PROGRESS, db_index=True)
    started_at = models.DateTimeField()
    expires_at = models.DateTimeField(db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    correct_count = models.PositiveSmallIntegerField(null=True, blank=True)
    incorrect_count = models.PositiveSmallIntegerField(null=True, blank=True)
    unanswered_count = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at", "-pk"]
        constraints = [models.UniqueConstraint(fields=["user", "mock_test"], condition=Q(state="in_progress"), name="exam_one_active_attempt_uniq")]
        indexes = [models.Index(fields=["user", "-started_at"], name="exam_attempt_history_idx")]

    def __str__(self):
        """Return the student's attempt label for staff administration."""
        return f"{self.user} — {self.mock_test} ({self.state})"


class AttemptResponse(models.Model):
    """Store the current selected option for one attempt question."""

    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name="responses")
    mock_test_question = models.ForeignKey(MockTestQuestion, on_delete=models.PROTECT, related_name="responses")
    selected_option = models.ForeignKey(QuestionOption, null=True, blank=True, on_delete=models.PROTECT, related_name="attempt_responses")
    saved_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["attempt", "mock_test_question"], name="exam_attempt_question_response_uniq")]

    def clean(self):
        """Ensure the selected answer belongs to this test question."""
        super().clean()
        if self.selected_option_id and self.mock_test_question_id:
            if self.selected_option.question_id != self.mock_test_question.question_id:
                raise ValidationError({"selected_option": "Selected option does not belong to this question."})

    def __str__(self):
        """Return the response's attempt and question position."""
        return f"Attempt {self.attempt_id}, question {self.mock_test_question.position}"
