import time
import requests
import json
import random


class LLMAdapter:
    def stream_tokens(self, prompt, clear_context=False):
        raise NotImplementedError


class DummyAdapter(LLMAdapter):
    def stream_tokens(self, prompt, clear_context=False):
        words = ["likes", "words", "and", "everyone", "playing", "with"]

        for i in range(10):
            time.sleep(0.5)
            word = random.choice(words)
            yield word + " "

        yield random.choice(words)


class RemoteLLMAdapter(LLMAdapter):
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def stream_tokens(self, prompt, clear_context=False):
        if clear_context:
            url = f"http://{self.host}:{self.port}/clear-context"
            resp = requests.post(url)
            if resp.status_code != 200:
                raise ClearContextError("Failed to clear context")

        url = f"http://{self.host}:{self.port}/completion"
        payload = {"prompt": prompt, "n_predict": 256, "stream": True}

        headers = {'Content-Type': 'application/json'}
        resp = requests.post(url, data=json.dumps(payload), headers=headers, stream=True)
        for line in resp.iter_lines(chunk_size=1):
            if line:
                line = line.decode('utf-8')

                stripped_line = line[6:]
                print("in Remote adapter!:", line, "stripped line:", stripped_line)
                entry = json.loads(stripped_line)
                if entry["stop"]:
                    break
                yield entry["content"]


class ClearContextError(Exception):
    pass
