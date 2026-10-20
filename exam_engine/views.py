"""Serve public test descriptions and owner-scoped examination workflows.

Views keep authorization and input handling at the HTTP boundary while
``services`` owns transactional attempt state and score calculations. Active
exam templates receive option text only; answer keys are queried only for a
finalized result page.
"""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from access_control.services import user_can_access

from .models import MockTest, MockTestQuestion, TestAttempt
from .services import TestUnavailable, finalize_expired_attempts, load_attempt, save_answer as save_attempt_answer, start_test as start_test_attempt, submit_attempt


def mock_test_list(request):
    """Show public descriptions for tests published by staff."""
    page_obj = Paginator(MockTest.objects.filter(is_published=True).order_by("title"), 20).get_page(request.GET.get("page"))
    return render(request, "exam_engine/mock_test_list.html", {"page_obj": page_obj, "mock_tests": page_obj.object_list})


def mock_test_detail(request, test_slug):
    """Show a published test description without exposing its questions."""
    mock_test = get_object_or_404(MockTest, slug=test_slug)
    if not user_can_access(request.user, is_published=mock_test.is_published, is_public=True):
        raise Http404
    question_count = mock_test.test_questions.count()
    now = timezone.now()
    is_available = not (
        (mock_test.available_from and now < mock_test.available_from)
        or (mock_test.available_until and now >= mock_test.available_until)
    )
    return render(request, "exam_engine/mock_test_detail.html", {
        "mock_test": mock_test,
        "question_count": question_count,
        "is_available": is_available,
    })


@require_POST
def start_test(request, test_slug):
    """Start or resume an authenticated student's available test attempt."""
    if not request.user.is_authenticated:
        next_url = reverse("exam_engine:mock_test_detail", args=[test_slug])
        return redirect(f"{reverse('login')}?{urlencode({'next': next_url})}")
    try:
        attempt = start_test_attempt(request.user, test_slug)
    except TestUnavailable:
        raise Http404
    return redirect("exam_engine:attempt_detail", attempt_id=attempt.pk)


@login_required
@never_cache
def attempt_detail(request, attempt_id):
    """Render an owned active attempt or its finalized score and review."""
    try:
        attempt = load_attempt(request.user, attempt_id)
    except TestAttempt.DoesNotExist:
        raise Http404
    if attempt.state != TestAttempt.State.IN_PROGRESS:
        test_questions = list(
            attempt.mock_test.test_questions.select_related("question")
            .prefetch_related("question__options")
            .order_by("position")
        )
        responses = {
            response.mock_test_question_id: response
            for response in attempt.responses.select_related("selected_option").all()
        }
        return render(request, "exam_engine/attempt_result.html", {
            "attempt": attempt,
            "test_questions": test_questions,
            "responses": responses,
        })

    test_questions = list(
        MockTestQuestion.objects.filter(mock_test=attempt.mock_test, question__is_published=True)
        .select_related("question")
        .prefetch_related("question__options")
        .order_by("position")
    )
    responses = {
        response.mock_test_question_id: response.selected_option_id
        for response in attempt.responses.all()
    }
    return render(request, "exam_engine/attempt_exam.html", {
        "attempt": attempt,
        "test_questions": test_questions,
        "responses": responses,
        "now": timezone.now(),
    })


@login_required
@require_POST
def save_answer(request, attempt_id):
    """Save or clear one owned response using server-validated identifiers."""
    mock_test_question_id = request.POST.get("mock_test_question_id")
    if not mock_test_question_id or not mock_test_question_id.isdecimal():
        return JsonResponse({"error": "A valid test question is required."}, status=400)
    try:
        result = save_attempt_answer(
            request.user,
            attempt_id,
            int(mock_test_question_id),
            None if request.POST.get("clear_answer") == "1" else request.POST.get("selected_option_id"),
        )
    except TestAttempt.DoesNotExist:
        raise Http404
    except ValidationError as error:
        return JsonResponse({"error": error.messages[0]}, status=400)
    if not result.was_saved:
        return JsonResponse({"error": "This attempt is locked.", "state": result.attempt.state}, status=409)
    response = result.attempt.responses.get(mock_test_question_id=mock_test_question_id)
    return JsonResponse({"saved": True, "saved_at": response.saved_at.isoformat()})


@login_required
@require_POST
def submit_test_attempt(request, attempt_id):
    """Finalize the owned attempt and safely redirect duplicate submits."""
    try:
        submit_attempt(request.user, attempt_id)
    except TestAttempt.DoesNotExist:
        raise Http404
    return redirect("exam_engine:attempt_detail", attempt_id=attempt_id)


@login_required
@never_cache
def attempt_history(request):
    """Show only the signed-in student's own attempts and result states."""
    finalize_expired_attempts(request.user)
    page_obj = Paginator(
        TestAttempt.objects.filter(user=request.user).select_related("mock_test"), 20
    ).get_page(request.GET.get("page"))
    return render(request, "exam_engine/attempt_history.html", {"page_obj": page_obj, "attempts": page_obj.object_list})
