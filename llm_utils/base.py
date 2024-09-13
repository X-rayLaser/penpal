from dataclasses import dataclass


class TokenGenerator:
    def __call__(self, text):
        raise NotImplementedError

    def set_spec(self, sampling_config, stop_word):
        pass


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
    voice_id: str = ''

    def to_dict(self):
        return self.__dict__
