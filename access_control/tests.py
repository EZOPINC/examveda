"""Verify the shared access policy fails closed for restricted resources."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from .services import user_can_access, user_has_entitlement


class SharedAccessPolicyTests(TestCase):
    """Check public, unpublished and future-entitlement decisions."""

    def test_published_public_resource_is_available_to_visitor_and_student(self):
        """Public publication policy does not require an account."""
        student = get_user_model().objects.create_user(username="access-student", password="Long-random-password-782!")
        self.assertTrue(user_can_access(AnonymousUser(), is_published=True, is_public=True))
        self.assertTrue(user_can_access(student, is_published=True, is_public=True))

    def test_unpublished_and_restricted_resources_fail_closed(self):
        """Draft or restricted content needs publication and a verified grant."""
        student = get_user_model().objects.create_user(username="restricted-student", password="Long-random-password-782!")
        self.assertFalse(user_can_access(student, is_published=False, is_public=True))
        self.assertFalse(user_can_access(AnonymousUser(), is_published=True, is_public=False))
        self.assertFalse(user_can_access(student, is_published=True, is_public=False))
        self.assertFalse(user_can_access(
            student,
            is_published=True,
            is_public=False,
            entitlement_code="membership:premium",
        ))

    def test_entitlement_lookup_is_closed_until_verified_entitlements_exist(self):
        """No browser-controlled state can grant access in this phase."""
        student = get_user_model().objects.create_user(username="no-entitlement", password="Long-random-password-782!")
        self.assertFalse(user_has_entitlement(student, "membership:premium"))
