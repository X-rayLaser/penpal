import datetime


llm_tools = {}


def register(name):
    def decorate(func):
        llm_tools[name] = func
        return func

    return decorate


@register("calculate")
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
