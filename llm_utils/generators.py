import requests
import json
from pygentify.llm_backends import GenerationSpec
from pygentify.llm_backends import LlamaCpp
from .base import TokenGenerator


class RequestMaker:
    def __init__(self, proxies=None):
        self.proxies = proxies or {}

    def get(self, *args, **kwargs):
        if self.proxies:
            kwargs["proxies"] = self.proxies
        return requests.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        if self.proxies:
            kwargs["proxies"] = self.proxies
        return requests.post(*args, **kwargs)


class RemoteLLM(TokenGenerator):
    def __init__(self, host, port, proxies=None):
        self.host = host
        self.port = port
        self.proxies = proxies or {}
        self.request_maker = RequestMaker(proxies)

    def stream_tokens(self, generation_spec):
        prompt = generation_spec.prompt
        llm_settings = generation_spec.sampling_config or {}
        inference_config = generation_spec.inference_config or {}
        clean_llm_settings(llm_settings)

        start_llm_url = f"http://{self.host}:{self.port}/start-llm"
        data = {
            'repo_id': inference_config.get('model_repo'),
            'file_name': inference_config.get('file_name'),
            'launch_params': inference_config.get('launch_params')
        }

        headers = {'Content-Type': 'application/json'}

        resp = self.request_maker.post(start_llm_url, data=json.dumps(data), headers=headers)
        if resp.status_code != 200:
            raise PrepareModelError("Failed to configure and start model")

        if generation_spec.clear_context:
            url = f"http://{self.host}:{self.port}/clear-context"
            resp = self.request_maker.post(url)
            if resp.status_code != 200:
                raise ClearContextError("Failed to clear context")

        url = f"http://{self.host}:{self.port}/completion"

        stop_word = "</api>"
        payload = {"prompt": prompt, "stream": True, "stop": [stop_word], "cache_prompt": True}
        payload.update(llm_settings)

        resp = self.request_maker.post(url, data=json.dumps(payload), headers=headers, stream=True)
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


class LlamaCppServer(TokenGenerator):
    def __init__(self, endpoint, proxies):
        self.endpoint = endpoint
        self.proxies = proxies
        self.generation_spec = None

    def set_spec(self, sampling_config, stop_word):
        self.generation_spec = GenerationSpec(sampling_config, stop_word)

    def __call__(self, text):
        llm = LlamaCpp(self.endpoint, self.generation_spec, self.proxies)
        yield from llm(text)


def clean_llm_settings(llm_settings):
    clean_float_field(llm_settings, 'temperature')
    clean_float_field(llm_settings, 'top_k')
    clean_float_field(llm_settings, 'top_p')
    clean_float_field(llm_settings, 'min_p')
    clean_float_field(llm_settings, 'repeat_penalty')
    clean_int_field(llm_settings, 'n_predict')


def clean_float_field(llm_settings, field):
    """Make sure that the value of the field is float, if field exists"""
    clean_any_field(llm_settings, field, float)


def clean_int_field(llm_settings, field):
    """Make sure that the value of the field is int, if field exists"""
    clean_any_field(llm_settings, field, int)


def clean_any_field(llm_settings, field, target_type):
    """Make sure that the value of the field is of target_type if field exists"""
    if field in llm_settings:
        llm_settings[field] = target_type(llm_settings[field])


class ClearContextError(Exception):
    pass


class PrepareModelError(Exception):
    pass


class DownloadStartFailed(Exception):
    pass
