from pathlib import Path

import typer
from rich.console import Console

__name__ = "News Image Extractor"
__help_description__ = (
    "Extractor for displaying, downloading, and bulk-uploading images"
)

ROOT = Path(__file__).parents[1]


class ExtractorTyper(typer.Typer):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name=__name__,
            help=__help_description__,
            add_completion=False,
            *args,
            **kwargs,
        )
        self.console = Console()
