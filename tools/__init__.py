import os
from .base import llm_tools
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
            spec = f.read()
            tools_with_specs.append((tool, spec))

    full_spec = ''
    if tools_with_specs:
        tools_str = '\n'.join(tool for tool, _ in tools_with_specs)

        full_spec = prefix_template.format(tools_str)

        for tool, spec in tools_with_specs:
            full_spec += f'\n{tool_spec_template.format(tool=tool, spec=spec)}'

        full_spec = full_spec + postfix_template
    return full_spec
