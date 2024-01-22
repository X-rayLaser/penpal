import time
import requests
import json
import random


class LLMAdapter:
    def stream_tokens(self, prompt, clear_context=False, llm_settings=None):
        raise NotImplementedError


class DummyAdapter(LLMAdapter):
    def stream_tokens(self, prompt, clear_context=False, llm_settings=None):
        words = ["likes", "words", "and", "everyone", "playing", "with"]

        for i in range(10):
            time.sleep(0.125)
            word = random.choice(words)
            yield word + " "

        yield random.choice(words)


class DummyMarkdownAdapter(LLMAdapter):
    def stream_tokens(self, prompt, clear_context=False, llm_settings=None):
        tokens = ["Of", " ", "course", ".", " ", "Here" " ", "is", " ", "the", " ", "code", ":", "\n", 
                  "``", "`", "python", "\n", "for", " ", "i", " in", " ", "range", "(", "5", ")", 
                  ":", "\n", "    ", "print", "(", "'", "hello", " ", "world", "'", ")", "\n", "```"]
        for token in tokens:
            time.sleep(0.125)
            yield token


class DummyToolUseAdapter(LLMAdapter):
    def stream_tokens(self, prompt, clear_context=False, llm_settings=None):
        tokens1 = ["one ", "two ", "three ", "<", "api>", "calculator", 
                  "(+,", "2,3)", "</api>", " rest", " to be ", "discarded "]
        tokens2 = ["four", "five", "six"]
        
        seq = tokens1 if random.random() > 0.5 else tokens2
        for token in seq:
            time.sleep(0.5)
            yield token


class RemoteLLMAdapter(LLMAdapter):
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
