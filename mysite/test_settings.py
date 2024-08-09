import os
from mysite.base_settings import *

print("LOADED TEST SETTINGS FILE!")

DEBUG = True

ALLOWED_HOSTS = []

LLM_SETTINGS = {
    "generator": {
        "class": "llm_utils.dummy_generators.DummyGenerator",
        "kwargs": {}
    }
}

TTS_BACKEND = {
    "class": "tts.backends.RemoteTtsBackend",
    "kwargs": {
        "host": "tts_mock",
        "port": 9300,
        "use_tls": False
    }
}


STT_BACKEND = {
    "class": "stt.backends.NullSpeechToTextBackend"
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/data/test_db.sqlite3',
    }
}