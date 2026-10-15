"""Validate editorial page and resource metadata in Django admin."""

from django import forms

from .models import ContentPage, ResourceFile, ResourceMetadata, Topic


class TopicForm(forms.ModelForm):
    """Apply model taxonomy validation to topic edits."""

    class Meta:
        model = Topic
        fields = "__all__"


class ContentPageForm(forms.ModelForm):
    """Validate publication content before staff saves a page."""

    class Meta:
        model = ContentPage
        fields = "__all__"


class ResourceMetadataForm(forms.ModelForm):
    """Validate cross-taxonomy metadata relationships in the admin."""

    class Meta:
        model = ResourceMetadata
        fields = "__all__"


class ResourceFileForm(forms.ModelForm):
    """Validate PDF type and size before it is stored."""

    class Meta:
        model = ResourceFile
        fields = "__all__"
