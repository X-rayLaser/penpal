from django.conf import settings
from import_utils import instantiate_class
from .backends import BaseTtsBackend, NullTtsBackend, DummyTtsBackend, RemoteTtsBackend


tts_backend_config = settings.TTS_BACKEND
tts_backend = instantiate_class(tts_backend_config)
