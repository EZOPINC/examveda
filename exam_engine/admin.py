"""Configure question/test authoring and read-only attempt administration."""

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext as _

from .forms import MockTestQuestionInlineFormSet, QuestionOptionInlineFormSet, QuestionOptionTranslationInlineFormSet, has_started_attempt
from .models import AttemptResponse, MockTest, MockTestQuestion, MockTestTranslation, Question, QuestionOption, QuestionOptionTranslation, QuestionTranslation, TestAttempt


class QuestionOptionInline(admin.TabularInline):
    """Edit choices as a group so the answer key can be validated together."""

    model = QuestionOption
    formset = QuestionOptionInlineFormSet
    extra = 4
    ordering = ["position"]

    def get_formset(self, request, obj=None, **kwargs):
        """Validate option completeness against the publication checkbox in this POST."""
        formset = super().get_formset(request, obj, **kwargs)
        formset.parent_is_published = request.POST.get("is_published") == "on" if request.method == "POST" else bool(obj and obj.is_published)
        return formset

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


class MockTestTranslationInline(admin.TabularInline):
    """Edit localized test labels and publication status alongside shared rules."""

    model = MockTestTranslation
    extra = 0
    readonly_fields = ["preview"]

    @admin.display(description="Editorial preview")
    def preview(self, obj):
        """Show the localized test metadata together for review before publication."""
        if not obj or not obj.pk:
            return _("Save the translation to preview its text.")
        return format_html("<strong>{}</strong><p>{}</p><p>{}</p>", obj.title, obj.description, obj.instructions)

    def get_readonly_fields(self, request, obj=None):
        """Keep translated wording fixed after attempts while allowing locale closure."""
        if has_started_attempt(obj):
            return [field.name for field in self.model._meta.fields if field.name != "is_published"] + ["preview"]
        return super().get_readonly_fields(request, obj)

    def has_add_permission(self, request, obj=None):
        """Require localized variants to exist before attempts begin."""
        return not has_started_attempt(obj) and super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Preserve localized test metadata referenced by attempt history."""
        return not has_started_attempt(obj) and super().has_delete_permission(request, obj)


class QuestionOptionTranslationInline(admin.TabularInline):
    """Translate every stable option identity under one question-language record."""

    model = QuestionOptionTranslation
    formset = QuestionOptionTranslationInlineFormSet
    extra = 0

    def get_formset(self, request, obj=None, **kwargs):
        """Validate every localized option when this request publishes its parent row."""
        formset = super().get_formset(request, obj, **kwargs)
        formset.parent_is_published = request.POST.get("is_published") == "on" if request.method == "POST" else bool(obj and obj.is_published)
        return formset

    def get_queryset(self, request):
        """Avoid loading option translations unrelated to the selected question locale."""
        return super().get_queryset(request).select_related("option", "question_translation")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit option choices to the logical question being translated."""
        if db_field.name == "option" and request.resolver_match and request.resolver_match.kwargs.get("object_id"):
            translation = QuestionTranslation.objects.filter(pk=request.resolver_match.kwargs["object_id"]).only("question_id").first()
            if translation:
                kwargs["queryset"] = QuestionOption.objects.filter(question_id=translation.question_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def _has_question_attempts(self, obj):
        """Return whether this translation's logical question is in an attempt."""
        return bool(obj and TestAttempt.objects.filter(mock_test__test_questions__question_id=obj.question_id).exists())

    def get_readonly_fields(self, request, obj=None):
        """Freeze localized option labels after their first attempt."""
        if self._has_question_attempts(obj):
            return [field.name for field in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

    def has_add_permission(self, request, obj=None):
        """Disallow new option labels after attempt history exists."""
        return not self._has_question_attempts(obj) and super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Preserve option labels used to render historical attempts."""
        return not self._has_question_attempts(obj) and super().has_delete_permission(request, obj)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Manage question text and answer options under Django permissions."""

    list_display = ["id", "subject", "topic", "language", "is_published", "translation_status", "updated_at"]
    list_filter = ["is_published", "language", "subject"]
    search_fields = ["prompt", "explanation"]
    inlines = [QuestionOptionInline]
    readonly_fields = ["translation_link"]

    def get_queryset(self, request):
        """Prefetch option and translation data used by the completeness column."""
        return super().get_queryset(request).prefetch_related("options", "translations__option_translations")

    @admin.display(description="Other language translations")
    def translation_link(self, obj):
        """Link staff to the separate translation editor with its option translations."""
        if not obj or not obj.pk:
            return _("Save the source question before adding translations.")
        return format_html('<a href="{}?question__id__exact={}">{}</a>', reverse("admin:exam_engine_questiontranslation_changelist"), obj.pk, _("Manage question translations"))

    @admin.display(description="Translation completeness")
    def translation_status(self, obj):
        """Show published/incomplete status per language without exposing answer keys."""
        statuses = []
        for translation in obj.translations.all():
            labels = {row.option_id: row.text for row in translation.option_translations.all()}
            option_ids = {option.pk for option in obj.options.all()}
            source_options = list(obj.options.all())
            complete = obj.is_published and len(source_options) >= 2 and sum(option.is_correct for option in source_options) == 1
            complete = complete and bool(translation.prompt.strip()) and option_ids == set(labels) and all(label.strip() for label in labels.values())
            if obj.explanation.strip() and not translation.explanation.strip():
                complete = False
            state = _("published") if translation.is_published else _("draft")
            if not complete:
                state = _("incomplete")
            statuses.append(f"{translation.language_code}: {state}")
        return ", ".join(statuses) or _("No translations")

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

    def get_formset(self, request, obj=None, **kwargs):
        """Validate test composition against the publication checkbox in this POST."""
        formset = super().get_formset(request, obj, **kwargs)
        formset.parent_is_published = request.POST.get("is_published") == "on" if request.method == "POST" else bool(obj and obj.is_published)
        return formset

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

    list_display = ["title", "language", "duration_minutes", "is_published", "available_languages", "available_from", "available_until"]
    list_filter = ["is_published"]
    search_fields = ["title", "slug", "description"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [MockTestQuestionInline, MockTestTranslationInline]
    readonly_fields = ["created_by", "created_at", "updated_at"]

    def get_queryset(self, request):
        """Load authored variants in batches for the ready-language status column."""
        return super().get_queryset(request).prefetch_related(
            "translations",
            "test_questions__question__options",
            "test_questions__question__translations__option_translations__option",
        )

    def save_model(self, request, obj, form, change):
        """Record the creating staff user for audit visibility."""
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_prepopulated_fields(self, request, obj=None):
        """Disable slug JavaScript when the immutable test identity is read-only."""
        if has_started_attempt(obj):
            return {}
        return super().get_prepopulated_fields(request, obj)

    def get_readonly_fields(self, request, obj=None):
        """Keep historical test content fixed but allow staff to close new starts."""
        if has_started_attempt(obj):
            return [*super().get_readonly_fields(request, obj), "title", "slug", "description", "instructions", "language", "duration_minutes"]
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Preserve tests referenced by student attempts."""
        return not has_started_attempt(obj) and super().has_delete_permission(request, obj)

    @admin.display(description="Ready languages")
    def available_languages(self, obj):
        """Show only languages that pass the same server readiness check as test starts."""
        from .services import available_test_languages

        labels = dict(available_test_languages(obj))
        return ", ".join(labels.values()) or _("None; review missing translations")


@admin.register(QuestionTranslation)
class QuestionTranslationAdmin(admin.ModelAdmin):
    """Manage translated question text, publication and matching option labels."""

    list_display = ["question", "language_code", "is_published", "completeness_status"]
    list_filter = ["language_code", "is_published"]
    search_fields = ["question__prompt", "prompt", "explanation"]
    autocomplete_fields = ["question"]
    inlines = [QuestionOptionTranslationInline]
    readonly_fields = ["question_source_language", "completeness_status", "translation_preview"]

    def get_queryset(self, request):
        """Prefetch source options and localized labels for status and preview columns."""
        return super().get_queryset(request).select_related("question").prefetch_related(
            "question__options", "option_translations__option"
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Prevent selecting a question whose wording is already in attempt history."""
        if db_field.name == "question":
            kwargs["queryset"] = Question.objects.exclude(
                test_questions__mock_test__attempts__isnull=False
            ).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def _has_question_attempts(self, obj):
        """Return whether the logical question's wording has been used in an attempt."""
        return bool(obj and TestAttempt.objects.filter(mock_test__test_questions__question_id=obj.question_id).exists())

    def get_readonly_fields(self, request, obj=None):
        """Freeze localized content after attempts while permitting publication closure."""
        if self._has_question_attempts(obj):
            return [field.name for field in self.model._meta.fields if field.name not in {"is_published"}] + [
                "question_source_language", "completeness_status", "translation_preview"
            ]
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Preserve question translations referenced by attempt history."""
        return not self._has_question_attempts(obj) and super().has_delete_permission(request, obj)

    @admin.display(description="Source question language")
    def question_source_language(self, obj):
        """Display the source language for comparison while editing a translation."""
        return obj.question.get_language_display() if obj and obj.pk else ""

    @admin.display(description="Translation completeness")
    def completeness_status(self, obj):
        """Identify missing option text and required explanations before publishing."""
        if not obj or not obj.pk:
            return _("Save the translation and add every option before publishing.")
        source_options = list(obj.question.options.all())
        option_ids = {option.pk for option in source_options}
        labels = {row.option_id: row.text for row in obj.option_translations.all()}
        complete = obj.question.is_published and len(source_options) >= 2 and sum(option.is_correct for option in source_options) == 1
        complete = complete and bool(obj.prompt.strip()) and option_ids == set(labels) and all(value.strip() for value in labels.values())
        if obj.question.explanation.strip() and not obj.explanation.strip():
            complete = False
        return _("Complete") if complete else _("Incomplete: add translated prompt, required explanation, and every option label.")

    @admin.display(description="Question preview")
    def translation_preview(self, obj):
        """Render escaped localized prompt, option labels, and explanation for staff review."""
        if not obj or not obj.pk:
            return _("Save the translation to preview it.")
        labels = [row.text for row in obj.option_translations.all()]
        options = format_html_join("", "<li>{}</li>", ((label,) for label in labels))
        explanation = format_html("<p><strong>{}</strong> {}</p>", _("Explanation:"), obj.explanation) if obj.explanation else ""
        return format_html("<div lang='{}'><strong>{}</strong><ul>{}</ul>{}</div>", obj.language_code, obj.prompt, options, explanation)

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
