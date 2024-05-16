import requests
import wave
import subprocess


class BaseSpeechToTextBackend:
    def __call__(self, audio):
        return ""


class NullSpeechToTextBackend(BaseSpeechToTextBackend):
    pass


class DummySpeechToTextBackend(BaseSpeechToTextBackend):
    def __call__(self, audio):
        print("Audio length: ", len(audio))
        return "This is a speech transcribed by DummySpeechToTextBackend backend"


class RemoteSpeechToTextBackend(BaseSpeechToTextBackend):
    endpoint = "/inference"

    def __init__(self, host, port, use_tls=True):
        self.host = host
        self.port = port
        self.use_tls = use_tls

    def __call__(self, audio):
        opus_path = "test_data/my_speech1.opus"
        wav_path = "test_data/output.wav"
        with open(opus_path, "wb") as f:
            f.write(audio)
        print("file is created!!!")

        subprocess.run(f'ffmpeg -i {opus_path} -ar 16000 -ac 1 -c:a pcm_s16le {wav_path} -y', shell=True,  check=True)
        
        protocol = "http"
        if self.use_tls:
            protocol += "s"
        
        url = f"{protocol}://{self.host}:{self.port}{self.endpoint}"

        headers = {'Accept': 'application/json'}
        files = {'file': open(wav_path, 'rb')}
        resp = requests.post(url, files=files, headers=headers)

        files['file'].close()

        result = None
        if resp.status_code == 200:
            result = resp.json()["text"]
        else:
            # log this
            pass

        return result
