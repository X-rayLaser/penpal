import os
from mysite.base_settings import *

print("LOADED TEST SETTINGS FILE!")

DEBUG = True

ALLOWED_HOSTS = []

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

LLM_SETTINGS = {
    "generator": {
        "class": "llm_utils.dummy_generators.DummyGenerator",
        "kwargs": {}
    }
}

TTS_BACKEND = {
    "class": "tts.backends.DummyTtsBackend",
    "kwargs": {
        "audio_file": "test_data/sample.wav"
    }
}


STT_BACKEND = {
    "class": "stt.backends.DummySpeechToTextBackend"
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/data/test_db.sqlite3',
    }
}