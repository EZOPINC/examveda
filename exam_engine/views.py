"""Serve public test descriptions and owner-scoped examination workflows.

Views keep authorization and input handling at the HTTP boundary while
``services`` owns transactional attempt state and score calculations. Active
exam templates receive option text only; answer keys are queried only for a
finalized result page.
"""

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import get_language, override
from django.utils.translation import gettext as _
from django.utils.http import urlencode
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from access_control.services import user_can_access

from .models import MockTest, MockTestQuestion, TestAttempt
from .services import (
    TestUnavailable,
    available_test_languages,
    change_attempt_language,
    finalize_expired_attempts,
    load_attempt,
    save_answer as save_attempt_answer,
    start_test as start_test_attempt,
    submit_attempt,
    test_language_content,
)


def _with_test_content(queryset):
    """Prefetch authored variants needed to determine and render available languages."""
    return queryset.prefetch_related(
        "translations",
        "test_questions__question__options",
        "test_questions__question__translations__option_translations__option",
    )


def _present_questions(attempt, review=False):
    """Prepare one language's prompt and options while omitting active answer keys."""
    language_code = attempt.language_code
    if language_code is None:
        # Legacy attempts predate a selected language; preserve their recorded source wording.
        questions = list(
            MockTestQuestion.objects.filter(mock_test=attempt.mock_test)
            .select_related("question")
            .prefetch_related("question__options")
            .order_by("position")
        )
        return [
            {
                "test_question": test_question,
                "language_code": test_question.question.language,
                "prompt": test_question.question.prompt,
                "explanation": test_question.question.explanation,
                "options": [
                    {
                        "id": option.pk,
                        "text": option.text,
                        **({"is_correct": option.is_correct} if review else {}),
                    }
                    for option in test_question.question.options.all()
                ],
            }
            for test_question in questions
        ]

    localized = test_language_content(attempt.mock_test, language_code, allow_closed=True)
    if localized is None:
        raise Http404
    return [
        {
            "test_question": item["test_question"],
            "language_code": language_code,
            "prompt": item["prompt"],
            "explanation": item["explanation"],
            "options": [
                {
                    "id": option.pk,
                    "text": text,
                    **({"is_correct": option.is_correct} if review else {}),
                }
                for option, text in item["options"]
            ],
        }
        for item in localized["questions"]
    ]


def _attempt_test_metadata(attempt, language_code):
    """Use legacy source metadata for attempts that predate locale selection."""
    if attempt.language_code is None:
        return {
            "title": attempt.mock_test.title,
            "description": attempt.mock_test.description,
            "instructions": attempt.mock_test.instructions,
        }
    localized = test_language_content(attempt.mock_test, language_code, allow_closed=True)
    if localized is None:
        raise Http404
    return localized["metadata"]


def mock_test_list(request):
    """Show public descriptions for tests published by staff."""
    tests = [
        (mock_test, available_test_languages(mock_test))
        for mock_test in _with_test_content(MockTest.objects.filter(is_published=True).order_by("title"))
    ]
    tests = [(test, languages) for test, languages in tests if languages]
    page_obj = Paginator(tests, 20).get_page(request.GET.get("page"))
    test_cards = []
    for mock_test, languages in page_obj.object_list:
        selected_code = next((code for code, _label in languages if code == get_language()), languages[0][0])
        content = test_language_content(mock_test, selected_code)
        test_cards.append({"test": mock_test, "languages": languages, "content": content["metadata"]})
    return render(request, "exam_engine/mock_test_list.html", {
        "page_obj": page_obj,
        "test_cards": test_cards,
    })


def mock_test_detail(request, test_slug):
    """Show a published test description without exposing its questions."""
    mock_test = get_object_or_404(_with_test_content(MockTest.objects.all()), slug=test_slug)
    if not user_can_access(request.user, is_published=mock_test.is_published, is_public=True):
        raise Http404
    available_languages = available_test_languages(mock_test)
    if not available_languages:
        raise Http404
    requested_language = request.GET.get("lang") or request.LANGUAGE_CODE.split("-")[0]
    language_code = next((code for code, _label in available_languages if code == requested_language), available_languages[0][0])
    language_content = test_language_content(mock_test, language_code)
    question_count = mock_test.test_questions.count()
    now = timezone.now()
    is_available = not (
        (mock_test.available_from and now < mock_test.available_from)
        or (mock_test.available_until and now >= mock_test.available_until)
    )
    return render(request, "exam_engine/mock_test_detail.html", {
        "mock_test": mock_test,
        "language_code": language_code,
        "available_languages": available_languages,
        "test_content": language_content["metadata"],
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
        attempt = start_test_attempt(request.user, test_slug, language_code=request.POST.get("language_code"))
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
    language_code = attempt.language_code or request.LANGUAGE_CODE.split("-")[0]
    language_label = dict(settings.LANGUAGES).get(language_code, language_code)
    with override(language_code):
        if attempt.state != TestAttempt.State.IN_PROGRESS:
            localized_questions = _present_questions(attempt, review=True)
            test_questions = [item["test_question"] for item in localized_questions]
            responses = {
                response.mock_test_question_id: response
                for response in attempt.responses.select_related("selected_option").all()
            }
            return render(request, "exam_engine/attempt_result.html", {
                "attempt": attempt,
                "test_questions": test_questions,
                "localized_questions": localized_questions,
                "responses": responses,
                "language_label": language_label,
                "test_metadata": _attempt_test_metadata(attempt, language_code),
            })

        localized_questions = _present_questions(attempt)
        test_questions = [item["test_question"] for item in localized_questions]
        responses = {
            response.mock_test_question_id: response.selected_option_id
            for response in attempt.responses.all()
        }
        return render(request, "exam_engine/attempt_exam.html", {
            "attempt": attempt,
            "test_questions": test_questions,
            "localized_questions": localized_questions,
            "responses": responses,
            "now": timezone.now(),
            "available_languages": [
                (code, label) for code, label in available_test_languages(
                    _with_test_content(MockTest.objects.filter(pk=attempt.mock_test_id)).get(),
                    allow_test_closed=True,
                )
            ],
            "language_label": language_label,
            "test_metadata": _attempt_test_metadata(attempt, language_code),
        })


@login_required
@require_POST
def change_test_language(request, attempt_id):
    """Change an owned active attempt's display language without touching its answers or timer."""
    language_code = request.POST.get("language_code", "")
    try:
        changed = change_attempt_language(request.user, attempt_id, language_code)
    except TestAttempt.DoesNotExist:
        raise Http404
    except ValidationError:
        from django.contrib import messages
        messages.error(request, _("This test is not available in the selected language."))
        return redirect("exam_engine:attempt_detail", attempt_id=attempt_id)
    if not changed:
        return redirect("exam_engine:attempt_detail", attempt_id=attempt_id)
    return redirect("exam_engine:attempt_detail", attempt_id=attempt_id)


@login_required
@require_POST
def save_answer(request, attempt_id):
    """Save or clear one owned response using server-validated identifiers."""
    mock_test_question_id = request.POST.get("mock_test_question_id")
    if not mock_test_question_id or not mock_test_question_id.isdecimal():
        return JsonResponse({"error": _("A valid test question is required.")}, status=400)
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
        return JsonResponse({"error": _("This attempt is locked."), "state": result.attempt.state}, status=409)
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
    attempt_cards = []
    for attempt in page_obj.object_list:
        if attempt.language_code:
            content = test_language_content(attempt.mock_test, attempt.language_code, allow_closed=True)
            title = content["metadata"]["title"] if content else attempt.mock_test.title
        else:
            title = attempt.mock_test.title
        attempt_cards.append({"attempt": attempt, "title": title})
    return render(request, "exam_engine/attempt_history.html", {
        "page_obj": page_obj,
        "attempt_cards": attempt_cards,
    })
