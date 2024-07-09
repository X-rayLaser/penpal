import os
from mysite.base_settings import *

print("LOADED PRODUCTION SETTINGS FILE!")

DEBUG = False

ALLOWED_HOSTS = ['localhost']

host_address = os.environ.get('SERVER_IP_ADDRESS')
if host_address:
    ALLOWED_HOSTS = [host_address]

llm_host = os.environ.get('LLM_HOST', "localhost")
stt_host = os.environ.get('STT_HOST', llm_host)
tts_host = os.environ.get('TTS_HOST', llm_host)

llm_port = os.environ.get('LLM_PORT', 9100)
stt_port = os.environ.get('STT_PORT', llm_port + 100)
tts_port = os.environ.get('TTS_PORT', stt_port + 100)

proxies = {}

http_proxy = os.environ.get('HTTP_PROXY_SERVER_ADDRESS')
https_proxy = os.environ.get('HTTPS_PROXY_SERVER_ADDRESS', http_proxy)

if http_proxy:
    proxies['http'] = http_proxy

if https_proxy:
    proxies['https'] = https_proxy

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
