from django.urls import path
from rest_framework import routers

from . import views

urlpatterns = [
    path('repos/', views.list_repositories),
    path('repo-detail/', views.list_gguf_files),
    path('start-download/', views.start_download),
    path('get-download-status/', views.get_download_status),
    path('downloads-in-progress/', views.get_downloads_in_progress),
    path('installed-models/', views.get_installed_models)
]