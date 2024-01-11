from django.urls import path
from rest_framework import routers

from . import views


router = routers.DefaultRouter()
router.register("system_messages", views.SystemMessageViewSet)

urlpatterns = [
    path('generate_reply/', views.generate_reply),
    path('completion/', views.generate_completion),
    path('call_api/', views.call_api),
    path('chats/', views.chat_list),
    path('chats/<int:pk>/', views.chat_detail),
    path('treebanks/<int:pk>/', views.treebank_detail),
    path('messages/', views.message_list),
    path('messages/<int:pk>/', views.message_detail)
]

urlpatterns += router.urls
