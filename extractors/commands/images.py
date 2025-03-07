# ---TECHNICAL DETAILS---
# Downloading all images are done on a single thread and process, but are launched concurrently.
# In short, all files are downloaded asynchronously using Python's asyncio with performance improvements from uvloop (winloop is used for windows platforms).
# The actual information obtained is from "news.csv" in the root directory, and only links that start with citris.ucmerced.edu are selected for extraction.
# Effectively, this means that all news posts linking to external sites are not counted towards content extraction.

import asyncio
import csv
import os
import re
import time
from functools import wraps
from itertools import chain
from pathlib import Path
from typing import Annotated, Any, Optional
from urllib.parse import quote, unquote

import aiohttp
import humanize
import msgspec
import typer
from aiofile import async_open
from bs4 import BeautifulSoup
from rich.console import Console
from rich.tree import Tree
from yarl import URL

from core import ROOT, ExtractorTyper

if os.name == "nt":
    from winloop import run
else:
    from uvloop import run

__description__ = (
    "Commands for finding associated images within news entries and other operations"
)


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return run(f(*args, **kwargs))

    return wrapper


### Structs


# Frozen to prevent adjustments, an also makes it slightly faster
# https://jcristharif.com/msgspec/structs.html#frozen-instances
class NewsImage(msgspec.Struct, frozen=True):
    local: Optional[Path]
    link: str


class NewsFile(msgspec.Struct):
    id: str
    title: str
    link: str
    images: Optional[list[NewsImage]] = None

    def to_dict(self) -> dict[str, Any]:
        return {f: getattr(self, f) for f in self.__struct_fields__}


### Utility


class CatchTime:
    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, type, value, traceback):
        self.time = time.perf_counter() - self.start


### Main extractor


class ImageExtractor:
    """Extractor logic"""

    def __init__(self, root: Path):
        self.root = root
        self.console = Console()
        self.link_regex = re.compile(r"^(http|https)://")
        self._csv_file = self.root / "news.csv"
        self._encoder = msgspec.json.Encoder(enc_hook=self._enc_hook)

        # This is a list as we have multiple rows within our csv file.
        # We are guaranteed to have multiple. If's it just one, then it just a dict
        self._db: dict[str, NewsFile] = {}
        self._load_from_file()

    ### Setup logic

    def _enc_hook(self, obj: Any) -> Any:
        if isinstance(obj, Path):
            return str(obj)
        return obj

    def _load_from_file(self) -> None:
        def extract_link_to_id(id: str, link: str) -> str:
            if not id:
                url = URL(unquote(link)).with_suffix("")
                return url.parts[-1].lower()
            return id

        try:
            with open(self._csv_file, "r") as f:
                self._db: dict[str, NewsFile] = {
                    entry["ID"]: NewsFile(
                        id=entry["ID"],
                        title=entry["TITLE"],
                        link=entry["LINK"],
                    )
                    for entry in csv.DictReader(f, delimiter=",")
                    if entry["LINK"].startswith("https://citris.ucmerced.edu/news")
                }
        except FileNotFoundError:
            self._db = {}

    ### Injection methods

    def _bulk_inject(self) -> dict[str, NewsFile]:
        for _, entry in self._db.items():
            entry.images = self.extract_images(entry)

        return self._db

    ### Public helper methods

    def extract_images(self, entry: NewsFile) -> Optional[list[NewsImage]]:
        """Extracts all images from a NewsFile intance

        Args:
            entry (NewsFile): NewsFile instance

        Raises:
            FileNotFoundError: If the `news.csv` file is no found

        Returns:
            Optional[list[NewsImage]]: List of all of the images, both in FS format and link format.
            If no images are found, returns None.
        """
        parsed_links = unquote(entry.link)
        news_link = (
            URL(parsed_links).with_suffix(".html")
            if not URL(parsed_links).suffix
            else URL(parsed_links)
        )

        proposed_file = self.root.joinpath(*news_link.parts[1:])
        url = URL.build(scheme="https", host="citris.ucmerced.edu")

        try:
            with open(proposed_file, "r") as f:
                soup = BeautifulSoup(f.read(), "lxml")
                raw_images: list[tuple[Optional[Path], str]] = []

                # Three main cases:
                # 1. Relative file, e.g.,  ../images/news/bioscape/aviLogo.png
                # 2. External links, e.g., https:/....
                # 3. Relative file but without "../" These are the rarest, thus not considered a priority. Same logic as 1

                for tag in soup.find_all("img"):
                    entity = str(tag["src"]).lstrip()  # type: ignore

                    if entity.startswith("../"):
                        raw_images.append(
                            (
                                Path(entity).resolve(),
                                str(url.with_path(entity.replace("../", "/"))),
                            )
                        )
                    elif self.link_regex.match(entity):
                        raw_images.append((None, str(URL(entity).with_query(None))))
                    else:
                        raw_images.append(
                            (Path(entity).resolve(), (str(url.with_path(entity))))
                        )

                if len(raw_images) == 0:
                    return

                return [
                    NewsImage(local=image[0], link=image[1]) for image in raw_images
                ]

        except FileNotFoundError:
            raise FileNotFoundError(
                "Cannot find HTML file. Is the proposed file path correct?"
            )

    def to_json(self, output: Optional[Path] = None) -> Optional[str]:
        """_summary_

        Args:
            output (Optional[Path], optional): Optional output path. Defaults to None.

        Returns:
            Optional[str]: Returns a str version of the encoded JSON.
            If specified an output, this returns None.
        """
        self._bulk_inject()

        encoded = self._encoder.encode(self._db)
        if output:
            Path.write_bytes(output, msgspec.json.format(encoded))
            return
        return encoded.decode()

    def display(self, local: bool = False) -> None:
        """Displays image paths/links through a tree

        Args:
            local (bool, optional): Whether to display local image paths. Defaults to False.
        """
        self._bulk_inject()
        tree = Tree(
            f"[bold white]Extracted Image Tree ({'Local FS' if local else 'CITRIS/External Links'})"
        )

        for file, entry in self._db.items():
            file_tree = tree.add(f"[gray]{file}")

            if not entry.images:
                continue

            for image in entry.images:
                file_tree.add(str(image.local if local else image.link))

        self.console.print(tree)

    def featured_display(self) -> None:
        """Finds the ID, and provides image informationm including file names and links."""

        def _handle_blanks(id: str) -> str:
            if len(id) == 0:
                return "/images/favicon.png"
            return f"/images/news/{id}.jpg"

        url = URL.build(scheme="https", host="citris.ucmerced.edu", path="")
        tree = Tree("[bold white]Featured Images Tree (All External + Local)")

        for file, entry in self._db.items():
            empty_file = (
                f"[gray]EMPTY - {entry.title}"
                if not entry.id and not file
                else f"[gray]{file}"
            )
            file_tree = tree.add(empty_file)

            if entry.id and file:
                file_tree.add(f"TITLE: {entry.title}")

            image = quote(_handle_blanks(entry.id))
            file_tree.add(f"LINK: {str(url.with_path(image))}")
            file_tree.add(f"IMAGE: {''.join(image.split('/')[-1])}")

        self.console.print(tree)

    def all(self) -> dict[str, NewsFile]:
        """Returns all entries within DB

        Returns:
            dict[str, NewsFile]: DB full of NewsFile instances
        """
        self._bulk_inject()
        return self._db


### CLI logic


app = ExtractorTyper()
extractor = ImageExtractor(ROOT)

### Commands and utilities


@app.command(name="show")
def show(
    local: Annotated[
        bool, typer.Option("--local", help="Displays the absolute path to images.")
    ] = False,
) -> None:
    """Shows the extracted content in a tree format"""
    extractor.display(local)


@app.command(name="featured")
def featured() -> None:
    """Displays information about the featured images for all posts (if possible)"""
    extractor.featured_display()


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
):
    """Outputs extracted content to JSON."""
    if output:
        extractor.to_json(output)
        app.console.print("Done!")
        return

    app.console.print_json(extractor.to_json())


async def download(
    url: URL, *, path: Path, session: aiohttp.ClientSession, chunk_size: int = 32768
):
    async with session.get(url) as response:
        async with async_open(path, "wb+") as afp:
            async for data in response.content.iter_chunked(chunk_size):
                await afp.write(data)


@app.command(name="mass-download")
@coro
async def mass_download(
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
    """Attempts to download all of the images extracted and found within news entries"""
    if not output:
        output = Path(__file__).parent / "news-images"

        if not output.exists():
            output.mkdir()
    else:
        if not output.is_dir():
            raise ValueError("Output is not a path!")

    total_images = 0
    images = {
        news_id: [images.link for images in chain(entry.images)]
        for news_id, entry in extractor.all().items()
        if entry.images
    }

    # This is not good, but there is really nothing I can do... - Noelle
    with app.console.status("[bold white]Downloading..."):
        async with aiohttp.ClientSession() as session:
            with CatchTime() as timer:
                async with asyncio.TaskGroup() as group:
                    for image_link in chain.from_iterable(
                        image for image in images.values()
                    ):
                        total_images += 1
                        image_url = URL(image_link)
                        filename = image_url.parts[-1]
                        group.create_task(
                            download(image_url, path=output / filename, session=session)
                        )
        app.console.print(
            f"[white]Done! Downloaded {total_images} images and took {humanize.naturaldelta(timer.time, minimum_unit='milliseconds')}"
        )
