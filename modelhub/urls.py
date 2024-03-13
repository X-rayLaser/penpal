from django.urls import path
from rest_framework import routers

from . import views

urlpatterns = [
    path('repos/', views.list_repositories),
    path('repo-detail/', views.list_gguf_files),
]