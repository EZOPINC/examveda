"""Validate student registration and account updates using Django's user forms."""

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm


class StudentRegistrationForm(UserCreationForm):
    """Create a standard student account without staff or permission fields."""

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username",)


class AccountDetailsForm(UserChangeForm):
    """Allow a student to update only the email field on their own account."""

    password = None

    class Meta:
        model = get_user_model()
        fields = ("email",)
