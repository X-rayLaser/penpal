import json
import requests


class BaseTtsBackend:
    def __call__(self, text):
        return None


class NullTtsBackend(BaseTtsBackend):
    pass


class DummyTtsBackend(BaseTtsBackend):
    def __init__(self, audio_file):
        self.audio_file = audio_file

    def __call__(self, text):
        with open(self.audio_file, "rb") as f:
            data = f.read()
        return data        


class RemoteTtsBackend(BaseTtsBackend):
    endpoint = "/tts/"

    def __init__(self, host, port, use_tls=True):
        self.host = host
        self.port = port
        self.use_tls = use_tls

    def __call__(self, text):
        protocol = "http"
        if self.use_tls:
            protocol += "s"
        
        url = f"{protocol}://{self.host}:{self.port}{self.endpoint}"
        body = {
            "text": text
        }
        headers = {'Content-Type': 'application/json'}
        resp = requests.post(url, data=json.dumps(body), headers=headers)

        audio = None
        if resp.status_code == 200:
            audio = resp.content
        else:
            # log this
            pass

        return audio
