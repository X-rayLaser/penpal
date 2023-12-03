import json
import importlib
from django.conf import settings

adapter_conf = settings.LLM_SETTINGS["adapter"]
adapter_path = adapter_conf["class"]
adapter_kwargs = adapter_conf["kwargs"]

parts = adapter_path.split(".")
module_path = ".".join(parts[:-1])
adapter_class = parts[-1]

cls = getattr(importlib.import_module(module_path), adapter_class)
adapter = cls(**adapter_kwargs)


def stream_tokens(prompt, clear_context=False, **settings):
    for token in adapter.stream_tokens(prompt, clear_context=clear_context, **settings):
        yield token


def clear_context():
    adapter.clear_context()