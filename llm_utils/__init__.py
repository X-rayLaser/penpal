import importlib
from django.conf import settings
from .base import GenerationSpec


conf = settings.LLM_SETTINGS["generator"]
generator_path = conf["class"]
generator_kwargs = conf["kwargs"]

parts = generator_path.split(".")
module_path = ".".join(parts[:-1])
generator_class = parts[-1]

cls = getattr(importlib.import_module(module_path), generator_class)
token_generator = cls(**generator_kwargs)

# todo: remove functions below, use token generator instance directly in views


def stream_tokens(generation_spec, **settings):
    for token in token_generator.stream_tokens(generation_spec, **settings):
        yield token


def start_download(repo, file_name, size):
    return token_generator.start_download(repo, file_name, size)


def get_downloads_in_progress():
    """Show information about all downloads in progress"""
    return token_generator.downloads_in_progress()


def get_failed_downloads():
    return token_generator.failed_downloads()


def get_download_status(repo_id, file_name):
    return token_generator.download_status(repo_id, file_name)


def get_installed_models():
    return token_generator.list_installed_models()
