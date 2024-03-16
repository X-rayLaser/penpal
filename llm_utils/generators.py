import requests
import json
from .base import TokenGenerator


class RemoteLLM(TokenGenerator):
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def stream_tokens(self, prompt, clear_context=False, llm_settings=None):
        llm_settings = llm_settings or {}
        clean_llm_settings(llm_settings)

        if clear_context:
            url = f"http://{self.host}:{self.port}/clear-context"
            resp = requests.post(url)
            if resp.status_code != 200:
                raise ClearContextError("Failed to clear context")

        url = f"http://{self.host}:{self.port}/completion"

        stop_word = "</api>"
        print(llm_settings)
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


class ManagedRemoteLLM(RemoteLLM):
    """LLM server must be stateful and it must implement these routes:
        - /clear-context
        - /completion
        - /download-llm
        - /download-status
        - /list-llms
        - /configure-llm
        - /start-llm
        - /stop-llm
    """
    def start_download(self, repo, file_name, size, llm_store='huggingface'):
        """Begins downloading a LLM on the server"""
        url = self.make_full_url("/download-llm")
        body = dict(repo=repo, file_name=file_name, size=size)
        return self.post_json(url, body)['download_id']

    def download_status(self, repo_id, file_name):
        url = self.make_full_url("/download-status")
        body = dict(repo_id=repo_id, file_name=file_name)
        return self.post_json(url, body)

    def downloads_in_progress(self):
        url = self.make_full_url("/downloads-in-progress")
        resp = requests.get(url)
        return resp.json()

    def list_installed_models(self):
        """Returns a list of models installed on the LLM server"""
        url = self.make_full_url("/list-models")
        resp = requests.get(url)
        return resp.json()

    def configure_llm(self, config):
        """Passes the LLM configuration to the server"""

    def start_llm(self):
        """Start/restart LLM specified by configure_llm method which must be called beforehand"""

    def stop_llm(self):
        """Stop running LLM on the server"""

    def make_full_url(self, path):
        return f"http://{self.host}:{self.port}{path}"

    def post_json(self, url, body):
        headers = {'Content-Type': 'application/json'}
        resp = requests.post(url, data=json.dumps(body), headers=headers)
        return resp.json()


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
