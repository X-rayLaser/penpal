import importlib
from django.conf import settings


def instantiate_class(config_dict):
    class_path = config_dict["class"]
    class_kwargs = config_dict.get("kwargs", {})

    parts = class_path.split(".")
    module_path = ".".join(parts[:-1])
    class_name = parts[-1]

    cls = getattr(importlib.import_module(module_path), class_name)
    return cls(**class_kwargs)
