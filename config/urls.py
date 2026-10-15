"""Map public foundation routes and configure Django error templates."""

from django.contrib import admin
from django.urls import include, path

from . import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("health/", views.health_check, name="health_check"),
    path("", include("content.urls")),
]

# Django renders templates/404.html and templates/500.html when DEBUG is False.
handler404 = "django.views.defaults.page_not_found"
handler500 = "django.views.defaults.server_error"
