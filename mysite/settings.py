"""
Django settings for mysite project.

Generated by 'django-admin startproject' using Django 4.2.6.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""
from mysite.base_settings import *

# SECURITY WARNING: don't run with debug turned on in production!
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

try:
    from mysite.local_settings import *
except ModuleNotFoundError:
    print("No module mysite.local_settings.py found")
