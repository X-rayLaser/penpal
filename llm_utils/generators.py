import requests
import json
from .base import TokenGenerator


class RemoteLLM(TokenGenerator):
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def stream_tokens(self, prompt, clear_context=False, llm_settings=None):
        llm_settings = llm_settings or {}

        if clear_context:
            url = f"http://{self.host}:{self.port}/clear-context"
            resp = requests.post(url)
            if resp.status_code != 200:
                raise ClearContextError("Failed to clear context")

        url = f"http://{self.host}:{self.port}/completion"

        stop_word = "</api>"
        payload = {"prompt": prompt, "stream": True, "stop": [stop_word]}
        payload.update(llm_settings)

        headers = {'Content-Type': 'application/json'}
        resp = requests.post(url, data=json.dumps(payload), headers=headers, stream=True)
        for line in resp.iter_lines(chunk_size=1):
            if line:
                line = line.decode('utf-8')

                stripped_line = line[6:]
                print("in Remote adapter!:", line, "stripped line:", stripped_line)
                entry = json.loads(stripped_line)
                if entry["stop"] and entry["stopping_word"] == stop_word:
                    yield stop_word
                    break
                yield entry["content"]


class ClearContextError(Exception):
    pass
