import asyncio
import csv
import datetime
import os
from enum import StrEnum
from functools import wraps
from pathlib import Path
from typing import Annotated, Any, Optional

import aiohttp
import msgspec
import typer
from aiofile import async_open
from dateutil.parser import parse
from rich.console import Console
from rich.tree import Tree
from yarl import URL

from core import ROOT, ExtractorTyper

if os.name == "nt":
    from winloop import run
else:
    from uvloop import run

__description__ = "Commands to extract and write external news entries"


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return run(f(*args, **kwargs))

    return wrapper


class OrderByChoices(StrEnum):
    asc = "asc"
    desc = "desc"


class ExternalNewsEntry(msgspec.Struct):
    id: str
    title: str
    link: str
    date: datetime.date
    description: str
    image_link: Optional[URL]

    def to_dict(self) -> dict[str, Any]:
        return {f: getattr(self, f) for f in self.__struct_fields__}

    def get_keys(self) -> list[str]:
        return [f for f in self.__struct_fields__]


class ExternalExtractor:
    def __init__(self, root: Path):
        self.root = root
        self.console = Console()

        self._csv_file = self.root / "news.csv"
        self._encoder = msgspec.json.Encoder(enc_hook=self._enc_hook)
        self._entries: list[ExternalNewsEntry] = []
        self._load_from_file()

    def _enc_hook(self, obj: Any) -> Any:
        if isinstance(obj, URL):
            return str(obj)
        return obj

    def _load_from_file(self) -> None:
        try:
            url = URL.build(scheme="https", host="citris.ucmerced.edu")
            with open(self._csv_file, "r") as f:
                self._entries: list[ExternalNewsEntry] = [
                    ExternalNewsEntry(
                        id="-".join(entry["TITLE"].lower().split(" "))
                        if not entry["ID"]
                        else entry["ID"],
                        date=parse(entry["DATE"]).date(),
                        image_link=url.with_path(f"/images/news/{entry['ID']}.jpg")
                        if entry["ID"]
                        else None,
                        **{
                            k.lower(): v.strip()
                            for k, v in entry.items()
                            if k not in ("ID", "DATE", "IMAGESIZE")
                        },
                    )
                    for entry in csv.DictReader(f, delimiter=",")
                    if not entry["LINK"].startswith(
                        (
                            "https://citris.ucmerced.edu/news",
                            "https://catpaws.ucmerced.edu",
                            "https://theleaflet.org",
                        )
                    )
                ]
        except FileNotFoundError:
            self._entries = []

    def to_markdown(
        self, output: Optional[Path] = None, *, reverse: bool = True
    ) -> str:
        """Writes/outputs entries in Markdown format

        Args:
            output (Path): Output path
            reverse (bool): Whether to sort asc/desc. Desc is reverse. Defaults to True.

        Returns:
            str: Returns the encoded entries in Markdown format.
        """

        if reverse:
            self._entries.sort(key=lambda x: x.date, reverse=reverse)
        flat_entries = [
            f"- [ ] {entry.title}\n\t- DATE: {entry.date}\n\t- LINK: {entry.link}\n\t- IMAGE_LINK: {entry.image_link}"
            for entry in self._entries
        ]
        encoded = "\n".join(entry for entry in flat_entries)

        if output:
            output.write_text(encoded)
        return encoded

    def to_json(self, output: Optional[Path] = None, *, reverse: bool = True) -> bytes:
        """Writes/outputs entries in JSON format

        Args:
            output (Path): Output path
            reverse (bool): Whether to sort asc/desc. Desc is reverse. Defaults to True.

        Returns:
            bytes: Returns the encoded entries in JSON format
        """
        if reverse:
            self._entries.sort(key=lambda x: x.date, reverse=reverse)

        encoded = self._encoder.encode(self._entries)
        if output:
            output.write_bytes(encoded)
        return encoded

    def write(self, output: Path, *, reverse: bool = True) -> None:
        """Public entrypoint to start writing all information down

        Args:
            output (Path): Output path. MUST be a csv fie
            reverse (bool): Whether to sort asc/desc. Desc is reverse. Defaults to True.

        Raises:
            ValueError: The file extension is not a CSV
        """
        if not output.suffix == ".csv":
            raise ValueError(
                "MUST be a CSV file! If you are looking for use JSON, use the json command"
            )
        if reverse:
            self._entries.sort(key=lambda x: x.date, reverse=reverse)

        with open(output, mode="w") as f:
            writer = csv.DictWriter(f, self._entries[0].get_keys())
            writer.writeheader()
            for entry in self._entries:
                writer.writerow(entry.to_dict())

    def display(self, *, reverse: bool = True) -> None:
        """Display extracted and sorted content via a tree-based format

        Args:
            reverse (bool): Whether to sort asc/desc. Defaults to True
        """
        tree = Tree("[bold white] Display with order_by sorted")
        if reverse:
            self._entries.sort(key=lambda x: x.date, reverse=reverse)

        for entry in self._entries:
            file_tree = tree.add(entry.title)
            file_tree.add(f"DATE: {entry.date}")
            file_tree.add(f"EXTERNAL LINK: {URL(entry.link).with_query(None)}")
            file_tree.add(f"THUMBNAIL LINK: {entry.image_link}")

        self.console.print(tree)

    def all(self) -> list[ExternalNewsEntry]:
        """Provides all of the entries in a public manner"""
        return self._entries


app = ExtractorTyper()
extractor = ExternalExtractor(ROOT)


@app.command(name="json")
def json(
    output: Annotated[
        Optional[Path],
        typer.Option(
            "--output",
            help="Outputs the JSON data to a file. No output means that it's piped to stdout",
            path_type=str,
            is_flag=True,
        ),
    ] = None,
    order_by: Annotated[
        OrderByChoices,
        typer.Option("--order-by", help="Order by asc/desc", is_flag=True),
    ] = OrderByChoices.desc,
):
    """Write or display JSON-formatted extracted data"""
    reverse_sort = True if order_by == "desc" else False

    if output:
        extractor.to_json(output, reverse=reverse_sort)
        app.console.print("Done!")
        return
    app.console.print_json(extractor.to_json(reverse=reverse_sort).decode())


@app.command(name="markdown")
def markdown(
    output: Annotated[
        Optional[Path],
        typer.Option(
            "--output",
            help="Outputs the JSON data to a file. No output means that it's piped to stdout",
            path_type=str,
            is_flag=True,
        ),
    ] = None,
    order_by: Annotated[
        OrderByChoices,
        typer.Option("--order-by", help="Order by asc/desc", is_flag=True),
    ] = OrderByChoices.desc,
):
    """Write or display Markdown formatted extracted data"""
    reverse_sort = True if order_by == "desc" else False
    if output:
        extractor.to_markdown(output, reverse=reverse_sort)
        app.console.print("Done!")

        return

    app.console.print(extractor.to_markdown(reverse=reverse_sort))


@app.command(name="write")
def write(
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            help="CSV output",
            path_type=str,
            is_flag=True,
        ),
    ] = ROOT / "debug" / "external-news-exporter.csv",
    order_by: Annotated[
        OrderByChoices,
        typer.Option("--order-by", help="Order by asc/desc", is_flag=True),
    ] = OrderByChoices.desc,
):
    """Write the extracted data into a CSV file"""
    reverse_sort = True if order_by == "desc" else False

    if output.suffix != ".csv":
        raise ValueError("Requested output MUST be a .csv file")

    with app.console.status("[bold white]Writing..."):
        extractor.write(output, reverse=reverse_sort)
        app.console.print(f"[white]Done! Wrote {len(extractor.all()) - 2} entries.")


@app.command(name="display")
def display(
    order_by: Annotated[
        OrderByChoices,
        typer.Option("--order-by", help="Order by asc/desc", is_flag=True),
    ] = OrderByChoices.desc,
) -> None:
    """Display extracted entries in a tree-like format or markdown in lists"""
    reverse_sort = True if order_by == "desc" else False

    extractor.display(reverse=reverse_sort)


async def download(
    url: URL, *, path: Path, session: aiohttp.ClientSession, chunk_size: int = 32768
):
    async with session.get(url) as response:
        async with async_open(path, "wb+") as afp:
            async for data in response.content.iter_chunked(chunk_size):
                await afp.write(data)


@app.command(name="thumbnail-extract")
@coro
async def mass_thumbnail_extraction(
    output: Annotated[
        Optional[Path],
        typer.Option(
            "--output",
            help="Folder output for images. MUST be a path",
            path_type=str,
            is_flag=True,
        ),
    ] = None,
):
    """Mass-download external news thumbnails"""
    if not output:
        output = Path(__file__).parents[2] / "debug" / "external-thumbnails"

        if not output.exists():
            output.mkdir()

    else:
        if not output.is_dir():
            raise ValueError("Output is NOT a path!")

    total = 0
    thumbnails = [entry.image_link for entry in extractor.all() if entry.image_link]

    with app.console.status("[bold white]Downloading..."):
        async with aiohttp.ClientSession() as session:
            async with asyncio.TaskGroup() as group:
                for image in thumbnails:
                    total += 1
                    filename = image.parts[-1]
                    group.create_task(
                        download(image, path=output / filename, session=session)
                    )

    app.console.print(f"[white]Done! Downloaded {total}")
