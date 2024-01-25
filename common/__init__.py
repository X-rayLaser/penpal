import importlib


def instantiate_class(conf):
    full_path = conf["class"]
    kwargs = conf["kwargs"]

    parts = full_path.split(".")
    module_path = ".".join(parts[:-1])
    cls_str = parts[-1]

    cls = getattr(importlib.import_module(module_path), cls_str)
    return cls(**kwargs)
