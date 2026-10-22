"""Map public foundation routes and configure Django error templates."""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, reverse_lazy
from django.views.i18n import set_language

from content.sitemaps import BlogArticleSitemap, BlogCategorySitemap

from . import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page=reverse_lazy("home")), name="logout"),
    path("i18n/set-language/", set_language, name="set_language"),
    path("accounts/", include("accounts.urls")),
    path("", views.home, name="home"),
    path("health/", views.health_check, name="health_check"),
    path("sitemap.xml", sitemap, {"sitemaps": {"blog_articles": BlogArticleSitemap, "blog_categories": BlogCategorySitemap}}, name="sitemap"),
    path("", include("content.urls")),
    path("", include("exam_engine.urls")),
]

# Django renders templates/404.html and templates/500.html when DEBUG is False.
handler404 = "django.views.defaults.page_not_found"
handler500 = "django.views.defaults.server_error"
