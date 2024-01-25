import re
from .base import ApiFunctionCall, APICallBackend, ApiCallNotFoundError


class TaggedApiCallBackend(APICallBackend):
    open_tag = "<api>"
    result_open_tag = "<result>"
    error_open_tag = "<error>"

    def __init__(self, tools):
        self.tools = tools

    @property
    def open_apicall_tag(self):
        return self.get_apicall_open_tag()

    @property
    def close_apicall_tag(self):
        return self.get_apicall_close_tag()

    def get_close_tag(self, open_tag):
        start_of_tag = open_tag[0]
        tag_name = open_tag[1:-1]
        end_of_tag = open_tag[-1]
        return f'{start_of_tag}/{tag_name}{end_of_tag}'

    def get_apicall_open_tag(self):
        return self.open_tag

    def get_apicall_close_tag(self):
        if hasattr(self, 'close_tag'):
            return self.close_tag
        return self.get_close_tag(self.open_tag)

    def get_result_open_tag(self):
        return self.result_open_tag

    def get_result_close_tag(self):
        if hasattr(self, 'result_close_tag'):
            return self.result_close_tag
        return self.get_close_tag(self.result_open_tag)

    def get_error_open_tag(self):
        return self.error_open_tag

    def get_error_close_tag(self):
        if hasattr(self, 'error_close_tag'):
            return self.error_close_tag
        return self.get_close_tag(self.error_open_tag)

    def try_pattern(self, text, pattern):
        matcher = re.compile(pattern)
        results = matcher.findall(text)
        return results[0] if results else ''

    def find_api_call(self, text):
        text = text.lower()

        open_tag = self.get_apicall_open_tag()
        close_tag = self.get_apicall_close_tag()

        match, fixed_match = self.locate_and_clean_api_call(text, open_tag, close_tag)
        if not match:
            raise ApiCallNotFoundError

        try:
            offset = text.index(match)
        except ValueError:
            msg = "Found api call markup, but for some reason failed to pinpoint its position"
            print(msg)
            raise Exception(msg)
        s = fixed_match.replace(open_tag, "").replace(close_tag, "").strip()

        name_matcher = re.compile('^[a-z_]*')
        name = name_matcher.findall(s)[0]
        arg_string = ''

        if not s.endswith(")"):
            s += ")"

        args_matcher = re.compile('\((.*)\)')
        
        matches = args_matcher.findall(s)
        if matches:
            arg_string = matches[0]

        args = [arg.strip().lower() for arg in arg_string.split(',')]
        args = [arg for arg in args if arg]
        api_call = ApiFunctionCall(name, args)

        return api_call, offset

    def locate_and_clean_api_call(self, text, open_tag, close_tag):
        tag_start = open_tag[0]
        open_tag_prefix = open_tag[:-1]
        open_tag_suffix = open_tag[1:]
        close_tag_prefix = close_tag[:-1]
        close_tag_suffix = close_tag[1:]

        def fix_open_tag_prefix(s):
            return s.replace(open_tag_prefix, open_tag)

        def fix_open_tag_suffix(s):
            return s.replace(open_tag_suffix, open_tag).replace(
                f'{tag_start}/{open_tag}', close_tag
            )
        
        def fix_close_tag_prefix(s):
            return s.replace(close_tag_prefix, close_tag)

        def fix_close_tag_suffix(s):
            return s.replace(close_tag_suffix, close_tag)

        patterns = [(open_tag, close_tag, lambda s: s),
                    (open_tag_prefix, close_tag, fix_open_tag_prefix),
                    (open_tag_suffix, close_tag, fix_open_tag_suffix),
                    (open_tag, close_tag_suffix, fix_close_tag_suffix),
                    (open_tag, close_tag_prefix, fix_close_tag_prefix)]
        
        fixed_match = ''
        match = ''
        for pattern_open_tag, pattern_close_tag, fixer in patterns:
            pattern = f'{pattern_open_tag}.*{pattern_close_tag}'
            match = self.try_pattern(text, pattern)
            if match:
                fixed_match = fixer(match)
                break

        return match, fixed_match

    def make_api_call(self, api_call: ApiFunctionCall):
        func = self.tools.get(api_call.name)

        if func:
            try:
                result = func(*api_call.args)
                api_call_string = self.render_with_result(api_call, result)
            except Exception as e:
                print("Exception: ", repr(e), str(e))
                api_call_string = self.render_with_error(api_call, str(e))
        else:
            print("MISSING", api_call.name)
            api_call_string = self.render_with_tool_missing(api_call)

        return api_call_string

    def render_api_call(self, api_call: ApiFunctionCall):
        args_str = ', '.join(api_call.args)
        open_tag = self.get_apicall_open_tag()
        close_tag = self.get_apicall_close_tag()
        return f'{open_tag}{api_call.name}({args_str}){close_tag}'

    def render_with_result(self, api_call: ApiFunctionCall, result):
        call_str = self.render_api_call(api_call)
        result_open_tag = self.get_result_open_tag()
        result_close_tag = self.get_result_close_tag()
        return call_str + result_open_tag + str(result) + result_close_tag

    def render_with_tool_missing(self, api_call: ApiFunctionCall):
        error = f'Tool {api_call.name} is missing'
        return self.render_with_error(self, api_call, error)

    def render_with_error(self, api_call: ApiFunctionCall, error: str):
        call_str = self.render_api_call(api_call)
        error_open_tag = self.get_error_open_tag()
        error_close_tag = self.get_error_close_tag()
        return call_str + error_open_tag + error + error_close_tag
