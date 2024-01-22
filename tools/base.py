llm_tools = {}


def register(name):
    def decorate(func):
        llm_tools[name] = func
        return func

    return decorate
