import importlib
from pkgutil import iter_modules

from typer import Typer

app_commands = Typer()
command_modules = [module.name for module in iter_modules(__path__, f"{__package__}.")]

for command in command_modules:
    module = importlib.import_module(command)
    app_commands.add_typer(
        module.app,
        name="".join(module.__name__.split(".")[1:]),
        help=module.__description__,
    )  # type: ignore
