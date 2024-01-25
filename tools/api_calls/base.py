from urllib.parse import urlencode
from dataclasses import dataclass
from django.urls import reverse


@dataclass
class ApiFunctionCall:
    name: str
    args: list

    @property
    def url(self):
        return '/chats/api/'

    def todict(self):
        mapping = {
            'name': self.name,
            'arg_string': ','.join(self.args)
        }

        url = reverse('call_api')
        query_string = urlencode(mapping)
        url += f'?{query_string}'

        return {
            'name': self.name,
            'args': self.args,
            'url': url
        }

    def __eq__(self, other):
        return self.name == other.name and self.args == other.args


class APICallBackend:
    def __init__(self, tools):
        self.tools = tools

    def find_api_call(self, text):
        raise NotImplementedError


class ApiCallNotFoundError(Exception):
    pass
