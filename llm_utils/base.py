class TokenGenerator:
    def stream_tokens(self, prompt, clear_context=False, llm_settings=None):
        raise NotImplementedError


class GenerationError(Exception):
    pass
