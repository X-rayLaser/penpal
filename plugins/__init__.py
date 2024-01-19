import datetime
import os

prefix_template = """
You can use the following tools:
{}

Please, carefully read specification for each tool given below.
"""

tool_spec_template = """
BEGIN SPECIFICATION FOR "{tool}"

{spec}

END SPECIFICATION FOR "{tool}"
"""


def get_specification(configuration):
    tools_with_specs = []
    for tool in configuration.tools:
        tool = tool.lower()
        path = os.path.join(f"plugins/specs/{tool}.txt")
        if not os.path.exists(path):
            print(f"Could not find a specification file '{path}' for a tool {tool}")
            continue

        with open(path) as f:
            spec = f.read()
            tools_with_specs.append((tool, spec))

    full_spec = ''
    if tools_with_specs:
        tools_str = '\n'.join(tool for tool, _ in tools_with_specs)

        full_spec = prefix_template.format(tools_str)

        for tool, spec in tools_with_specs:
            full_spec += f'\n{tool_spec_template.format(tool=tool, spec=spec)}'

    return full_spec


llm_tools = {}


def register(name):
    def decorate(func):
        llm_tools[name] = func
        return func

    return decorate


@register("calculator")
def calculate(*args):
    if len(args) != 3:
        raise ValueError()
    
    operator = str(args[0])
    a = float(args[1])
    b = float(args[2])

    if operator == '+':
        return a + b
    
    if operator == '-':
        return a - b
    
    if operator == '*':
        return a * b

    if operator == '/':
        return a / b

    raise ValueError(f'Unsupported operator {operator}')


@register("current_date_time")
def current_time(*args):
    return str(datetime.datetime.now())
