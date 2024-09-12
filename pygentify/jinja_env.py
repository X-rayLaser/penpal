from jinja2 import Environment, PackageLoader, select_autoescape
env = Environment(
    loader=PackageLoader("pygentify"),
    autoescape=select_autoescape()
)