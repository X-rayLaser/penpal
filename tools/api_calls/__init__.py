from django.conf import settings
from .base import ApiFunctionCall, ApiCallNotFoundError
from ..base import llm_tools
from .backends import TaggedApiCallBackend
from common import instantiate_class


config = settings.LLM_SETTINGS.get("api_call_backend")


if config:
    backend = instantiate_class(config)
else:
    backend = TaggedApiCallBackend(llm_tools)


def find_api_call(text):
    return backend.find_api_call(text)


def make_api_call(api_call):
    return backend.make_api_call(api_call)


def render_api_call(api_call, result=None, error=None):
    if result:
        return backend.render_with_result(api_call, result)
    if error:
        return backend.render_with_error(api_call, error)
    
    return backend.render_api_call(api_call)
