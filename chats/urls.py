from django.urls import path
from rest_framework import routers

from . import views


router = routers.DefaultRouter()
router.register("system_messages", views.SystemMessageViewSet)
router.register("presets", views.PresetViewSet)
router.register("configurations", views.ConfigurationViewSet)
router.register("speech-samples", views.SpeechSampleViewSet)

urlpatterns = [
    path('generate_reply/', views.generate_reply),
    path('transcribe_speech/', views.transcribe_speech),
    path('completion/', views.generate_completion),
    path('chats/', views.ChatList.as_view()),
    path('chats/<int:pk>/', views.chat_detail),
    path('treebanks/<int:pk>/', views.treebank_detail),
    path('messages/', views.message_list),
    path('messages/<int:pk>/', views.message_detail),
    path('tools-spec/', views.tools_specification),
    path('supported-tools/', views.supported_tools),
    path('list-voices/', views.list_voices),
    path('voice-sample/', views.VoiceSampleView.as_view())
]

urlpatterns += router.urls
