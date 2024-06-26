from dataclasses import dataclass


class TokenGenerator:
    def stream_tokens(self, generation_spec):
        raise NotImplementedError


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
