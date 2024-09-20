import re
import json
import os
from dataclasses import dataclass
from inspect import signature
from .chat_render import ChatRendererToString, default_template
from .jinja_env import env


def find_tool_use(s):
    pattern = r"\<\|tool_use_start\|\>([^<]*)<\|tool_use_end\|>"
    match = re.search(pattern, s)
    if match:
        return match.start(), len(match.group(0)), match.group(1)
    else:
        raise ToolUseNotFoundError("Tool use not found")


class ToolUseNotFoundError(Exception):
    pass


def contains_tool_use(s):
    try:
        find_tool_use(s)
        return True
    except ToolUseNotFoundError:
        return False


def parse_tool_use(text):
    try:
        data = json.loads(text)
        if 'tool_name' in data:
            return (data['tool_name'], data.get('args', {}))
        else:
            raise ValueError("Tool name not found in JSON string")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON string: {e}")


def render_tool_use_string(tool_name, arg_dict, result=None):
    data = {'tool_name': tool_name, 'args': arg_dict}
    result = result or ''
    return f'<|tool_use_start|>{json.dumps(data)}<|tool_use_end|><|result_start|>{result}<|result_end|>'


def render_tool_use_error(tool_name, arg_dict, error=None):
    data = {'tool_name': tool_name, 'args': arg_dict}
    error = error or ''
    return f'<|tool_use_start|>{json.dumps(data)}<|tool_use_end|><|error_start|>{error}<|error_end|>'


class ToolUse:
    def find(self, s):
        raise NotImplementedError

    def contains_tool_use(self, s):
        try:
            self.find(s)
            return True
        except ToolUseNotFoundError:
            return False

    def parse(self, text):
        raise NotImplementedError

    def render_tool_call(self, tool_name, arg_dict):
        raise NotImplementedError

    def render_raw_tool_call(self, body):
        raise NotImplementedError

    def render_result(self, tool_name, result):
        raise NotImplementedError

    def render_error(self, tool_name, error):
        raise NotImplementedError

    def render_syntax_error(self, error):
        raise NotImplementedError


@dataclass
class GenericToolUse(ToolUse):
    test: str
    call_template: str
    success_template: str
    error_template: str
    syntax_error_template: str = ""

    def find(self, s):
        pattern = self.test
        match = re.search(pattern, s)
        if match:
            return match.start(), len(match.group(0)), match.group(1)
        else:
            raise ToolUseNotFoundError("Tool use not found")

    def parse(self, text):
        try:
            data = json.loads(text)
            if 'tool_name' in data:
                return (data['tool_name'], data.get('args', {}))
            else:
                raise ValueError("Tool name not found in JSON string")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {e}")

    def render_tool_call(self, tool_name, arg_dict):
        data = {'tool_name': tool_name, 'args': arg_dict}
        body = json.dumps(data)
        return self.call_template.format(body)

    def render_raw_tool_call(self, body):
        return self.call_template.format(body)

    def render_result(self, tool_name, result):
        data = {'tool_name': tool_name, 'result': result}
        body = json.dumps(data)
        return self.success_template.format(body)

    def render_error(self, tool_name, error):
        data = {'tool_name': tool_name, 'error': error}
        body = json.dumps(data)
        return self.error_template.format(body)

    def render_syntax_error(self, error):
        return self.syntax_error_template.format(error)


class SimpleTagBasedToolUse(GenericToolUse):
    def __init__(self, start_tag, end_tag, result_start_tag, result_end_tag,
                 error_start_tag, error_end_tag):
        def escape(s):
            escape_chars = '<|>'
            for ch in escape_chars:
                s = s.replace(ch, "\\" + ch)
            return s

        call_template = f'{start_tag}{{}}{end_tag}'
        success_template = f'{result_start_tag}{{}}{result_end_tag}'
        error_template = f'{error_start_tag}{{}}{error_end_tag}'
        syntax_error_template = error_template

        self.start_tag = start_tag
        self.end_tag = end_tag

        start_tag = escape(start_tag)
        end_tag = escape(end_tag)
        error_start_tag = escape(error_start_tag)
        error_end_tag = escape(error_end_tag)

        test = f"{start_tag}(.*){end_tag}"
        super().__init__(test, call_template, success_template, error_template, syntax_error_template)

    @classmethod
    def create_default(cls):
        return cls(start_tag="<|tool_use_start|>",
                   end_tag="<|tool_use_end|>",
                   result_start_tag="<|result_start|>",
                   result_end_tag="<|result_end|>",
                   error_start_tag="<|error_start|>",
                   error_end_tag="<|error_end|>")

    def parse(self, text):
        try:
            return super().parse(text)
        except ValueError as e:
            text += '}'
            print("Value error, trying to recover with body:", text)
            # todo: even more robust behaviour, auto-correct more errors
            # todo: consider to use custom recovery strategies for fixing simple cases
            try:
                return super().parse(text)
            except:
                raise e



def find_code(response):
    start_str = end_str = "```"
    language = None

    PYTHON_LANG = 'python'
    JS_LANG = 'javascript'

    try:
        idx_start = response.index(start_str)
        prefix = response[:idx_start]
        try:
            idx_end = response.index(end_str, idx_start+1)
        except ValueError:
            idx_end = len(response)

        code = response[idx_start + len(start_str):idx_end]

        if code.lower().startswith(PYTHON_LANG):
            language = PYTHON_LANG
        
        if code.lower().startswith(JS_LANG):
            language = JS_LANG

        return prefix, code, language
    except ValueError:
        return None


tool_registry = {}


class ToolRegistrator:
    def __init__(self, name):
        self.name = name

    def __call__(self, func):
        tool_registry[self.name] = func
        return func


def register(name=None):
    def decorator(func):
        func_name = name or func.__name__
        tool_registry[func_name] = func
        return func
    
    return decorator


def default_tool_use_backend():
    return SimpleTagBasedToolUse.create_default()


def create_docs(tool_use_backend, **kwargs):
    tools = kwargs.get('tools', []) or []
    func_template = kwargs.get("func_doc_template", "function_doc.jinja")
    api_template = kwargs.get("api_doc_template", "api_doc.jinja")

    tools = map(normalize, tools)
    chosen_tools = [tool for tool in tools if tool["name"] in tool_registry]
    func_docs = []
    for tool in chosen_tools:
        doc_file = tool.get('doc_file')

        if doc_file and os.path.isfile(doc_file):
            doc_text = load_doc_file(doc_file)
        else:
            tool_name = tool['name']
            func = tool_registry[tool_name]
            doc_text = document_function(tool_name, func, tool_use_backend, func_template)
        func_docs.append(doc_text)

    template = env.get_template(api_template)
    return template.render(func_docs=func_docs)


def normalize(item):
    item = dict(name=item) if isinstance(item, str) else dict(item)
    item["name"] = item.get("name", "").lower()
    return item


def document_function(name, func, tool_use_helper, func_template):
    doc_str = func.__doc__ or "Documentation was not provided for the function"
    sig = signature(func)
    examples = []
    if hasattr(func, 'usage_examples'):
        for arg_dict in func.usage_examples:
            tool_use_str = tool_use_helper.render_tool_call(name, arg_dict)
            examples.append(tool_use_str)

    template = env.get_template(func_template)
    return template.render(name=name, signature=str(sig), doctext=doc_str, usage_examples=examples)


def load_doc_file(doc_file):
    with open(doc_file) as f:
        return f.read()
