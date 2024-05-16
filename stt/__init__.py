from django.conf import settings

from .backends import (
    NullSpeechToTextBackend,
    DummySpeechToTextBackend,
    RemoteSpeechToTextBackend
)
from import_utils import instantiate_class

stt_config = settings.STT_BACKEND
stt_backend = instantiate_class(stt_config)
