import os
import re
from .base import llm_tools
from .api_calls import backend, ApiFunctionCall
from . import default

try:
    from . import custom
except ImportError:
    print("Missing module tools.custom")

prefix_template = """
You can use the following tools:
{}

Please, carefully read specification for each tool given below.
Do not read the specification back to the user. They should not know these implementation details.
"""

tool_spec_template = """
BEGIN SPECIFICATION FOR "{tool}"

{spec}

END SPECIFICATION FOR "{tool}"
"""

postfix_template = """
Do not read the specification back to the user.
Users should not know these implementation details.

Normal interaction with user starts here.
"""


def get_specification(configuration):
    tools_with_specs = []
    for tool in configuration.tools:
        tool = tool.lower()
        default_path = os.path.join(f"tools/specs/default/{tool}.txt")
        custom_path = os.path.join(f"tools/specs/custom/{tool}.txt")

        if os.path.exists(default_path):
            path = default_path
        elif os.path.exists(custom_path):
            path = custom_path
        else:
            print(f"Could not find a specification file for a tool {tool}")
            continue
        
        with open(path) as f:
            template = f.read()
            spec = render_template(template)
            tools_with_specs.append((tool, spec))

    full_spec = ''
    if tools_with_specs:
        tools_str = '\n'.join(tool for tool, _ in tools_with_specs)

        full_spec = prefix_template.format(tools_str)

        for tool, spec in tools_with_specs:
            full_spec += f'\n{tool_spec_template.format(tool=tool, spec=spec)}'

        full_spec = full_spec + postfix_template
    return full_spec


def render_template(template):
    def make_pattern(base_pattern, action):
        return "{% " + base_pattern.format(action=action) + " %}"

    base_pattern = "{action} ([A-Za-z0-9\s\"\!\?\+\-\*\/]+)"

    api_call_pattern = make_pattern(base_pattern, action="apicall")
    pattern_with_result = make_pattern(base_pattern, action="call_with_result")
    pattern_with_error = make_pattern(base_pattern, action="call_with_error")

    template = re.sub(api_call_pattern, replace_apicall, template)

    template = re.sub(pattern_with_result, replace_call_with_result, template)
    return re.sub(pattern_with_error, replace_call_with_error, template)


def replace_apicall(match):
    func = replace(lambda name, args, last_arg: 
                   backend.render_api_call(ApiFunctionCall(name, args)))
    return func(match)


def replace_call_with_result(match):
    func = replace(lambda name, args, last_arg: 
                   backend.render_with_result(ApiFunctionCall(name, args[:-1]), last_arg))
    return func(match)


def replace_call_with_error(match):
    func = replace(lambda name, args, last_arg:
                   backend.render_with_error(ApiFunctionCall(name, args[:-1]), last_arg))
    return func(match)


def replace(render):
    def func(match):
        s = match.group(1)

        arguments = [arg.strip() for arg in s.split('"') if arg.strip()]

        if not arguments:
            raise ApiCallParseError('Api call expected to have at least 1 argument (the name)')
        
        api_name = arguments[0]
        api_args = arguments[1:]

        last_arg = api_args[-1]
        return render(api_name, api_args, last_arg)
    return func



class ApiCallParseError(Exception):
    pass
