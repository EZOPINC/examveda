"""Define the approved stable public content and staff-preview routes."""

from django.urls import path, re_path

from . import views

app_name = "content"

urlpatterns = [
    path("blog/", views.blog_index, name="blog_index"),
    path("blog/category/<slug:category_slug>/", views.blog_category, name="blog_category"),
    path("blog/images/<int:page_id>/", views.blog_featured_image, name="blog_featured_image"),
    path("blog/<slug:article_slug>/", views.blog_detail, name="blog_detail"),
    path("free-resources/", views.resource_list, name="resource_list"),
    path("free-resources/subjects/<slug:subject_slug>/", views.subject_list, name="subject_list"),
    path("free-resources/subjects/<slug:subject_slug>/topics/<slug:topic_slug>/", views.topic_list, name="topic_list"),
    path("free-resources/pages/<slug:page_slug>/", views.editorial_detail, name="editorial_detail"),
    path("free-resources/preview/<int:page_id>/", views.preview_page, name="preview_page"),
    path("free-resources/preview/<int:page_id>/featured-image/", views.preview_featured_image, name="preview_featured_image"),
    path("free-resources/files/<int:file_id>/", views.public_file, name="public_file"),
    path("free-resources/<slug:exam_slug>/<slug:subject_slug>/<slug:paper_slug>/", views.previous_paper_detail, name="previous_paper_detail"),
    re_path(r"^free-resources/(?P<exam_slug>[a-z0-9-]+)/(?P<stage_slug>[a-z0-9-]+)/(?P<year>[0-9]{4})/(?P<resource_type>[a-z0-9-]+)/(?P<resource_slug>[a-z0-9-]+)/$", views.resource_detail, name="resource_detail"),
    re_path(r"^free-resources/(?P<exam_slug>[a-z0-9-]+)/(?P<stage_slug>[a-z0-9-]+)/(?P<year>[0-9]{4})/(?P<resource_type>[a-z0-9-]+)/$", views.type_list, name="type_list"),
    re_path(r"^free-resources/(?P<exam_slug>[a-z0-9-]+)/(?P<stage_slug>[a-z0-9-]+)/(?P<year>[0-9]{4})/$", views.year_list, name="year_list"),
    # Keep the existing stage route first for reverse/resolve compatibility.
    # Its view falls back to an exam-scoped subject when no stage matches.
    path("free-resources/<slug:exam_slug>/<slug:stage_slug>/", views.stage_list, name="stage_list"),
    path("free-resources/<slug:exam_slug>/<slug:stage_slug>/", views.stage_list, name="exam_subject_list"),
    path("free-resources/<slug:exam_slug>/", views.category_list, name="category_list"),
]
