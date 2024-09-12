import math
import json
import time
import requests
from urllib.parse import urlparse
from .tool_calling import register


@register()
def add(num1:float, num2:float) -> float:
    """Add two numbers and returns their sum
    
    num1: first summand
    num2: second summand
    """
    return num1 + num2

add.usage_examples = [{"num1": 23, "num2": 19}, {"num1": -32, "num2": 9}]

@register()
def subtract(num1, num2):
    return num1 - num2


@register()
def multiply(num1, num2):
    return num1 * num2


@register()
def divide(num1, num2):
    """
    Divides first argument by second argument
    
    The second argument must not be zero, otherwise ZeroDivisionError will be raised
    """
    return num1 / num2


divide.usage_examples = [{"num1": 23, "num2": 12}, {"num1": 23, "num2": 1}, {"num1": 23, "num2": 22}]


@register()
def round(x):
    return round(x)


@register()
def sqrt(number):
    return math.sqrt(number)


@register()
def pow(num1, num2):
    return math.pow(num1, num2)


@register()
def sin(rads):
    return math.sin(rads)


@register()
def cos(rads):
    return math.cos(rads)


cos.usage_examples = [{"rads": 0.2}]


class SearchProvider:
    def search(self, query, **kwargs):
        return []


def get_web_search(provider):
    def search(query, **kwargs):
        try:
            results = provider.search(query, **kwargs)
            return json.dumps(results)
        except Exception:
            print("Exception")
            raise
    return search


@register()
def code_interpreter(code: str) -> dict:
    """Execute the code and get back captured stdout, stderr and return code

    Returns a dictionary of the form:
    {
        "stdout": "captured stdout when running the code",
        "stderr": "captured stderr showing errors during code execution",
        "return_code": "return code"
    }
    """
    import requests

    print("about to execute the code in 10 seconds!:\n", code)
    time.sleep(10)

    data = {
        "code": code
    }
    endpoint = "http://localhost:9800/run_code/"
    headers = headers={'content-type': 'application/json'}

    resp = requests.post(endpoint, data=json.dumps(data), headers=headers)

    
    if resp.ok:
        return resp.json()
    raise Exception(f'Failed to execute code: "{resp.reason}"')


def react_app_maker(component_code: str, css_code: str):
    """Creates a tiny React app by wrapping component's source code with trivial boilerplate code

    component_code should be either a functional component (a function) or class based component (a class).
    For example:
    function MainComponent(props) {
        return <div>Hello, world!</div>;
    }
    """

    print("about to send the code in 10 seconds!:\n", component_code)
    #time.sleep(10)

    data = {
        "js_code": component_code,
        "css_code": css_code
    }

    # todo: endpoint should be configurable
    endpoint = "http://172.17.0.1:9900/make_react_app/"
    headers = headers={'content-type': 'application/json'}
    resp = requests.post(endpoint, data=json.dumps(data), headers=headers)

    if resp.ok:
        return resp.json()
    raise Exception(f'Failed to create app: "{resp.reason}"')


code_interpreter.usage_examples = [
    {"code": "print(42)"}
]