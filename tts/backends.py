import json
import requests


class BaseTtsBackend:
    def synthesize(self, text, voice_id):
        return None

    def list_voices(self):
        return []


class NullTtsBackend(BaseTtsBackend):
    pass


class DummyTtsBackend(BaseTtsBackend):
    def __init__(self, audio_file):
        self.audio_file = audio_file

    def synthesize(self, text, voice_id):
        with open(self.audio_file, "rb") as f:
            data = f.read()
        return data        

    def list_voices(self):
        return ["Voice 1", "Voice 2", "Voice 3"]


class RemoteTtsBackend(BaseTtsBackend):
    endpoint = "/tts/"

    voices_endpoint = "/voices/"

    def __init__(self, host, port, use_tls=True, proxies=None):
        self.host = host
        self.port = port
        self.use_tls = use_tls
        self.proxies = proxies or {}

    def synthesize(self, text, voice_id):
        body = {
            "text": text,
            "voice_id": voice_id
        }
        resp = self.make_request(self.endpoint, requests.post, data=json.dumps(body))

        audio = None
        if resp.status_code == 200:
            audio = resp.content
        else:
            # log this
            pass

        return audio

    def list_voices(self):
        resp = self.make_request(self.voices_endpoint)
        if resp.status_code == 200:
            return resp.json()
        return []

    def make_request(self, endpoint, method=None, data=None):
        method = method or requests.get
        url = self.make_url(endpoint)
        headers = {'Content-Type': 'application/json'}
        return method(url, data, headers=headers, proxies=self.proxies)

    def make_url(self, path):
        protocol = "http"
        if self.use_tls:
            protocol += "s"
        
        return f"{protocol}://{self.host}:{self.port}{path}"