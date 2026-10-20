"""Define stable public test pages and authenticated attempt endpoints."""

from django.urls import path

from . import views

app_name = "exam_engine"

urlpatterns = [
    path("mock-tests/", views.mock_test_list, name="mock_test_list"),
    path("mock-tests/attempts/", views.attempt_history, name="attempt_history"),
    path("mock-tests/attempts/<int:attempt_id>/", views.attempt_detail, name="attempt_detail"),
    path("mock-tests/attempts/<int:attempt_id>/responses/", views.save_answer, name="save_answer"),
    path("mock-tests/attempts/<int:attempt_id>/submit/", views.submit_test_attempt, name="submit_attempt"),
    path("mock-tests/<slug:test_slug>/", views.mock_test_detail, name="mock_test_detail"),
    path("mock-tests/<slug:test_slug>/start/", views.start_test, name="start_test"),
]
