class TokenGenerator:
    def stream_tokens(self, prompt, inference_config=None, clear_context=False, llm_settings=None):
        raise NotImplementedError


class GenerationError(Exception):
    pass
