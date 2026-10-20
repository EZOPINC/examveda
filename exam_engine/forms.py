"""Validate inline authoring rules for questions and mock tests.

Django model validation checks individual records, while these formsets can
validate complete option lists and ordered test composition before admin saves.
"""

from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import MockTestQuestion, QuestionOption, TestAttempt


class QuestionOptionInlineFormSet(BaseInlineFormSet):
    """Require a complete single-choice answer key before question publication."""

    def clean(self):
        """Validate option count and exactly one correct option as a group."""
        super().clean()
        if any(self.errors):
            return
        if not self.instance.is_published:
            return
        active_options = [
            form.cleaned_data
            for form in self.forms
            if form.cleaned_data and form.cleaned_data.get("text") and not form.cleaned_data.get("DELETE")
        ]
        if len(active_options) < 2:
            raise ValidationError("A published question must have at least two answer options.")
        if sum(bool(option.get("is_correct")) for option in active_options) != 1:
            raise ValidationError("A published question must have exactly one correct answer option.")


class MockTestQuestionInlineFormSet(BaseInlineFormSet):
    """Require a published test to contain at least one valid question."""

    def clean(self):
        """Validate test composition after all inline rows are considered."""
        super().clean()
        if any(self.errors) or not self.instance.is_published:
            return
        active_questions = [
            form.cleaned_data
            for form in self.forms
            if form.cleaned_data and form.cleaned_data.get("question") and not form.cleaned_data.get("DELETE")
        ]
        if not active_questions:
            raise ValidationError("A published test must contain at least one question.")


def has_started_attempt(mock_test):
    """Return whether a saved test has an attempt and therefore is frozen."""
    return bool(mock_test and mock_test.pk and TestAttempt.objects.filter(mock_test=mock_test).exists())
