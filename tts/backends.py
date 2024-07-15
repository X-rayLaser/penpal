import json
import requests


class BaseTtsBackend:
    def synthesize(self, text, voice_id):
        return None

    def list_voices(self):
        return []

    def get_voice_sample(self, relative_url):
        return None


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
        return [{"voice_id": "Voice 1", "url": ""},
                {"voice_id": "Voice 2", "url": ""},
                {"voice_id": "Voice 3", "url": ""}]

    def get_voice_sample(self, relative_url):
        return self.synthesize(None, None)


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

    def get_voice_sample(self, voice_id):
        path = f'/voice-sample/?voice_id={voice_id}'
        return self.make_request(path).content

    def list_voices(self):
        try:
            resp = self.make_request(self.voices_endpoint)
        except requests.exceptions.ConnectionError:
            return []

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