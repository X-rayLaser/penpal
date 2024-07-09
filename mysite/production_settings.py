import os
from mysite.base_settings import *

print("LOADED PRODUCTION SETTINGS FILE!")

DEBUG = False

ALLOWED_HOSTS = ['localhost']

llm_host = os.environ.get('LLM_HOST', "localhost")
stt_host = os.environ.get('STT_HOST', llm_host)
tts_host = os.environ.get('TTS_HOST', llm_host)

llm_port = os.environ.get('LLM_PORT', 9100)
stt_port = os.environ.get('STT_PORT', llm_port + 100)
tts_port = os.environ.get('TTS_PORT', stt_port + 100)

proxies = {}

LLM_SETTINGS = {
    "generator": {
        "class": "llm_utils.generators.ManagedRemoteLLM",
        "kwargs": {
            "host": llm_host,
            "port": llm_port,
            "proxies": proxies
        }
    }
}


STT_BACKEND = {
    "class": "stt.backends.RemoteSpeechToTextBackend",
    "kwargs": {
        "host": stt_host,
        "port": stt_port,
        "use_tls": False,
        "proxies": proxies
    }
}

TTS_BACKEND = {
    "class": "tts.backends.RemoteTtsBackend",
    "kwargs": {
        "host": tts_host,
        "port": tts_port,
        "use_tls": False,
        "proxies": proxies
    }
}
