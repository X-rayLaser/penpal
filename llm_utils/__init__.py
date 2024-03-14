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


def start_download(repo_id, file_name):
    return token_generator.start_download(repo_id, file_name)


def get_downloads_in_progress():
    """Show information about all downloads in progress"""
    return token_generator.downloads_in_progress()


def get_download_status(download_id):
    return token_generator.download_status(download_id)


def get_installed_models():
    return token_generator.list_installed_models()
