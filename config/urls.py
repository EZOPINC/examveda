"""Map public foundation routes and configure Django error templates."""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, reverse_lazy

from . import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page=reverse_lazy("home")), name="logout"),
    path("accounts/", include("accounts.urls")),
    path("", views.home, name="home"),
    path("health/", views.health_check, name="health_check"),
    path("", include("content.urls")),
    path("", include("exam_engine.urls")),
]

# Django renders templates/404.html and templates/500.html when DEBUG is False.
handler404 = "django.views.defaults.page_not_found"
handler500 = "django.views.defaults.server_error"
