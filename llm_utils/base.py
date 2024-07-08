from dataclasses import dataclass


class TokenGenerator:
    def stream_tokens(self, generation_spec):
        raise NotImplementedError

    def start_download(self, repo, file_name, size, llm_store='huggingface'):
        return 0

    def download_status(self, repo_id, file_name):
        return {}

    def downloads_in_progress(self):
        return []

    def failed_downloads(self):
        return []

    def list_installed_models(self):
        return [{
            'repo_id': 'Dummy model',
            'repo': {},
            'file_name': 'dummy',
            'size': 0
        }]


class GenerationError(Exception):
    pass


@dataclass
class GenerationSpec:
    prompt: str
    inference_config: dict
    sampling_config: dict
    clear_context: bool
    parent_message_id: int
    image_b64: str = ''

    def to_dict(self):
        return self.__dict__
