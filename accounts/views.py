"""Handle public registration and authenticated student account pages.

Authentication, password hashing, sessions and password validation remain
provided by Django. Registration deliberately exposes no staff flags or roles.
"""

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .forms import AccountDetailsForm, StudentRegistrationForm


@require_http_methods(["GET", "POST"])
def register(request):
    """Register a least-privileged student and sign them into their account."""
    if request.user.is_authenticated:
        return redirect("accounts:profile")
    form = StudentRegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        student = form.save()
        login(request, student)
        return redirect("accounts:profile")
    return render(request, "accounts/register.html", {"form": form})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    """Show the signed-in user's account and allow updating their email only."""
    form = AccountDetailsForm(
        request.POST if request.method == "POST" else None,
        instance=request.user,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})
