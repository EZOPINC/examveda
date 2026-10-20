"""Configure question/test authoring and read-only attempt administration."""

from django.contrib import admin

from .forms import MockTestQuestionInlineFormSet, QuestionOptionInlineFormSet, has_started_attempt
from .models import AttemptResponse, MockTest, MockTestQuestion, Question, QuestionOption, TestAttempt


class QuestionOptionInline(admin.TabularInline):
    """Edit choices as a group so the answer key can be validated together."""

    model = QuestionOption
    formset = QuestionOptionInlineFormSet
    extra = 4
    ordering = ["position"]

    def get_readonly_fields(self, request, obj=None):
        """Freeze options with a question used by started attempts."""
        if obj and obj._has_started_attempt():
            return [field.name for field in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

    def has_add_permission(self, request, obj=None):
        """Disallow adding options after attempts capture the question."""
        return not (obj and obj._has_started_attempt()) and super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Disallow deleting options after attempts capture the question."""
        return not (obj and obj._has_started_attempt()) and super().has_delete_permission(request, obj)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Manage question text and answer options under Django permissions."""

    list_display = ["id", "subject", "topic", "language", "is_published", "updated_at"]
    list_filter = ["is_published", "language", "subject"]
    search_fields = ["prompt", "explanation"]
    inlines = [QuestionOptionInline]

    def get_readonly_fields(self, request, obj=None):
        """Protect question content after its first test attempt."""
        if obj and obj._has_started_attempt():
            return [field.name for field in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Preserve questions referenced by attempt history."""
        return not (obj and obj._has_started_attempt()) and super().has_delete_permission(request, obj)


class MockTestQuestionInline(admin.TabularInline):
    """Maintain test ordering and per-question scoring values."""

    model = MockTestQuestion
    formset = MockTestQuestionInlineFormSet
    extra = 1
    autocomplete_fields = ["question"]

    def get_readonly_fields(self, request, obj=None):
        """Make test composition read-only after the first attempt starts."""
        if has_started_attempt(obj):
            return [field.name for field in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

    def has_add_permission(self, request, obj=None):
        """Disallow additions after attempt history exists."""
        return not has_started_attempt(obj) and super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Disallow removals after attempt history exists."""
        return not has_started_attempt(obj) and super().has_delete_permission(request, obj)


@admin.register(MockTest)
class MockTestAdmin(admin.ModelAdmin):
    """Configure duration, availability, publication, and question order."""

    list_display = ["title", "duration_minutes", "is_published", "available_from", "available_until"]
    list_filter = ["is_published"]
    search_fields = ["title", "slug", "description"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [MockTestQuestionInline]
    readonly_fields = ["created_by", "created_at", "updated_at"]

    def save_model(self, request, obj, form, change):
        """Record the creating staff user for audit visibility."""
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        """Keep historical test content fixed but allow staff to close new starts."""
        if has_started_attempt(obj):
            return [*super().get_readonly_fields(request, obj), "title", "slug", "description", "duration_minutes"]
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Preserve tests referenced by student attempts."""
        return not has_started_attempt(obj) and super().has_delete_permission(request, obj)


@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    """Expose attempt summaries as read-only staff records."""

    list_display = ["user", "mock_test", "state", "started_at", "expires_at", "score"]
    list_filter = ["state", "mock_test"]
    search_fields = ["user__username", "mock_test__title"]
    readonly_fields = [field.name for field in TestAttempt._meta.fields]

    def has_add_permission(self, request):
        """Require attempts to be created through the student start service."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Preserve attempt history and score summaries."""
        return False


@admin.register(AttemptResponse)
class AttemptResponseAdmin(admin.ModelAdmin):
    """Allow staff to inspect saved answers without editing student work."""

    list_display = ["attempt", "mock_test_question", "selected_option", "saved_at"]
    list_filter = ["attempt__mock_test", "attempt__state"]
    search_fields = ["attempt__user__username", "attempt__mock_test__title"]
    readonly_fields = [field.name for field in AttemptResponse._meta.fields]

    def has_add_permission(self, request):
        """Ensure answers are written only through owner-checked endpoints."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Preserve response records for attempt review and audit."""
        return False
