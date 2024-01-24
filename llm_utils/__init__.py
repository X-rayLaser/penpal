import importlib
from django.conf import settings

conf = settings.LLM_SETTINGS["generator"]
generator_path = conf["class"]
generator_kwargs = conf["kwargs"]

parts = generator_path.split(".")
module_path = ".".join(parts[:-1])
generator_class = parts[-1]

cls = getattr(importlib.import_module(module_path), generator_class)
token_generator = cls(**generator_kwargs)


def stream_tokens(prompt, clear_context=False, llm_settings=None, **settings):
    for token in token_generator.stream_tokens(prompt, clear_context=clear_context,
                                               llm_settings=llm_settings, **settings):
        yield token
