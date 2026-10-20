"""Verify registration, self-service account controls and role boundaries."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AccountWorkflowTests(TestCase):
    """Exercise student account workflows using Django's built-in auth model."""

    def test_registration_creates_and_signs_in_a_student_not_an_admin(self):
        """Public registration creates only least-privileged student accounts."""
        response = self.client.post(reverse("accounts:register"), {
            "username": "new-student",
            "password1": "Long-random-password-782!",
            "password2": "Long-random-password-782!",
            "is_staff": "on",
            "is_superuser": "on",
        })

        student = get_user_model().objects.get(username="new-student")
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertFalse(student.is_staff)
        self.assertFalse(student.is_superuser)
        self.assertTrue(student.check_password("Long-random-password-782!"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), student.pk)

    def test_registration_rejects_duplicate_usernames(self):
        """The built-in creation form preserves username uniqueness validation."""
        get_user_model().objects.create_user(username="existing-student", password="Long-random-password-782!")
        response = self.client.post(reverse("accounts:register"), {
            "username": "existing-student",
            "password1": "Another-random-password-782!",
            "password2": "Another-random-password-782!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A user with that username already exists")

    def test_login_uses_django_authentication_and_redirects_to_account(self):
        """The established login route authenticates a registered student."""
        get_user_model().objects.create_user(username="login-student", password="Long-random-password-782!")
        response = self.client.post(reverse("login"), {
            "username": "login-student",
            "password": "Long-random-password-782!",
        })
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 200)

    def test_account_pages_require_authentication_and_are_user_scoped(self):
        """Anonymous requests are redirected and a profile shows only its owner."""
        first_student = get_user_model().objects.create_user(username="profile-one", password="Long-random-password-782!")
        get_user_model().objects.create_user(username="profile-two", password="Long-random-password-782!")
        profile_url = reverse("accounts:profile")
        self.assertRedirects(self.client.get(profile_url), f"/accounts/login/?next={profile_url}")

        self.client.force_login(first_student)
        response = self.client.get(profile_url)
        self.assertContains(response, "profile-one")
        self.assertNotContains(response, "profile-two")
        self.assertIn("no-store", response["Cache-Control"])

    def test_student_can_change_email_and_password(self):
        """The owner can update their email and use Django's password change flow."""
        student = get_user_model().objects.create_user(username="account-owner", password="Long-random-password-782!")
        self.client.force_login(student)
        response = self.client.post(reverse("accounts:profile"), {"email": "student@example.test"})
        self.assertRedirects(response, reverse("accounts:profile"))
        student.refresh_from_db()
        self.assertEqual(student.email, "student@example.test")

        response = self.client.post(reverse("accounts:password_change"), {
            "old_password": "Long-random-password-782!",
            "new_password1": "Another-long-password-913!",
            "new_password2": "Another-long-password-913!",
        })
        self.assertRedirects(response, reverse("accounts:password_change_done"))
        student.refresh_from_db()
        self.assertTrue(student.check_password("Another-long-password-913!"))

    def test_logout_uses_post_and_invalidates_the_session(self):
        """Sign out uses Django's built-in POST-only logout view."""
        student = get_user_model().objects.create_user(username="logout-owner", password="Long-random-password-782!")
        self.client.force_login(student)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, "/")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_only_staff_accounts_can_open_django_admin(self):
        """Student registrations cannot gain administrator access."""
        student = get_user_model().objects.create_user(username="ordinary-student", password="Long-random-password-782!")
        self.client.force_login(student)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

        administrator = get_user_model().objects.create_user(
            username="staff-administrator", password="Long-random-password-782!", is_staff=True
        )
        self.client.force_login(administrator)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        self.assertEqual(
            self.client.get(reverse("admin:exam_engine_mocktest_changelist")).status_code,
            403,
        )

        superuser = get_user_model().objects.create_superuser(
            username="platform-superuser", email="admin@example.test", password="Long-random-password-782!"
        )
        self.client.force_login(superuser)
        self.assertEqual(
            self.client.get(reverse("admin:exam_engine_mocktest_changelist")).status_code,
            200,
        )
