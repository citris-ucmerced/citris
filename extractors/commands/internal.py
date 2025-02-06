import csv
import datetime
import re
from pathlib import Path
from typing import Annotated, Any, Optional
from urllib.parse import unquote

import msgspec
import typer
from bs4 import BeautifulSoup
from dateutil.parser import parse
from rich.console import Console
from yarl import URL

from core import ROOT, ExtractorTyper

OUTPUT = Path(__file__).parent / "news-wp-exporter.csv"


class InternalNewsEntry(msgspec.Struct):
    id: str
    title: str
    link: str
    date: datetime.date
    description: str
    authors: Optional[str] = None
    content: Optional[str] = None
    imagesize: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {f: getattr(self, f) for f in self.__struct_fields__}

    def get_keys(self) -> list[str]:
        return [f for f in self.__struct_fields__]


class InternalExtractor:
    def __init__(self, root: Path, output: Path):
        self.root = root
        self.output = output
        self.console = Console()
        self._csv_file = self.root / "news.csv"
        self._encoder = msgspec.json.Encoder()

        # This is a list as we have multiple rows within our csv file.
        # We are guaranteed to have multiple. If's it just one, then it just a dict
        self._entries: list[InternalNewsEntry] = []
        self._load_from_file()

    def _load_from_file(self) -> None:
        try:
            with open(self._csv_file, "r") as f:
                self._entries: list[InternalNewsEntry] = [
                    InternalNewsEntry(
                        date=parse(entry["DATE"]).date(),
                        **{k.lower(): v for k, v in entry.items() if not k == "DATE"},
                    )
                    for entry in csv.DictReader(f, delimiter=",")
                    if entry["LINK"].startswith("https://citris.ucmerced.edu/news")
                ]
        except FileNotFoundError:
            self._entries = []

    def _bulk_inject(self, no_newline: bool = False) -> list[InternalNewsEntry]:
        for entry in self._entries:
            if not entry.id:
                entry.id = self.extract_link_to_id(entry)

            entry.authors = self.extract_authors(entry)
            entry.content = (
                self.extract_html(entry).replace("\n", "")
                if no_newline
                else self.extract_html(entry)
            )
        return self._entries

    def extract_link_to_id(self, entry: InternalNewsEntry) -> str:
        """Takes a InternalNewsEntry instance, grabs the link,
        and makes a new lowercased ID

        Args:
            entry (InternalNewsEntry): InternalNewsEntry instance

        Returns:
            str: The new lowercased ID
        """
        url = URL(unquote(entry.link)).with_suffix("")
        return url.parts[-1].lower()

    def extract_html(self, entry: InternalNewsEntry, section_only: bool = True) -> str:
        """Parses and extracts HTML news files and outputs the text of the file.

        Args:
            entry (InternalNewsEntry): InternalNewsEntry instance
            section_only (bool, optional): Whether to only parse the content between <section> tags. Defaults to True.

        Raises:
            FileNotFoundError: If the link cannot find the HTML file locally

        Returns:
            str: Text-based contents of the HTML file
        """
        parsed_links = unquote(entry.link)
        news_link = (
            URL(parsed_links).with_suffix(".html")
            if not URL(parsed_links).suffix
            else URL(parsed_links)
        )

        proposed_file = self.root.joinpath(*news_link.parts[1:])

        try:
            with open(proposed_file, "r") as f:
                soup = BeautifulSoup(f.read(), "lxml")

                if section_only:
                    section_text = "".join(
                        tag.get_text() for tag in soup.find_all("section")
                    )

                    # Fallback option to parse from the div class that has the content class. This seems to work for all html file
                    # This does produce some "outliers" in terms of the actual text, but the most efficient manner to handle them is by manual intervention
                    if len(section_text) == 0:
                        return "".join(
                            tag.get_text()
                            for tag in soup.find_all("div", class_="content")
                        )

                    return section_text

                return soup.get_text()

        except FileNotFoundError:
            raise FileNotFoundError(
                "Cannot find HTML file. Is the proposed file path correct?"
            )

    def extract_authors(self, entry: InternalNewsEntry) -> str:
        """Extract authors from news entry

        Args:
            entry (InternalNewsEntry): InternalNewsEntry instance

        Raises:
            FileNotFoundError: If the file cannot be found locally

        Returns:
            str: Known authors
        """
        parsed_links = unquote(entry.link)
        news_link = (
            URL(parsed_links).with_suffix(".html")
            if not URL(parsed_links).suffix
            else URL(parsed_links)
        )

        proposed_file = self.root.joinpath(*news_link.parts[1:])
        try:
            with open(proposed_file, "r") as f:
                soup = BeautifulSoup(f.read(), "lxml")
                return "".join(
                    tag.get_text()
                    for tag in soup.find_all("p", string=re.compile(r"^[B|b]y:.*"))
                )
        except FileNotFoundError:
            raise FileNotFoundError(
                "Cannot find HTML file. Is the proposed file path correct?"
            )

    def to_json(
        self, output: Optional[Path] = None, *, no_newline: bool = False
    ) -> bytes:
        """Writes/outputs entries in JSON format

        Args:
            output (Path): Output path

        Returns:
            bytes: Returns the encoded entries in JSON format
        """
        self._bulk_inject(no_newline)
        encoded = self._encoder.encode(self._entries)
        if output:
            output.write_bytes(encoded)
        return encoded

    def write(self, output: Path, *, no_newline: bool = False) -> None:
        """Public entrypoint to start extracting, parsing, and writing the content to the CSV file defined.

        Args:
            no_newline: Whether to strip all `\n` characters out from parsed HTML content. Defaults to False
        """
        if not output.suffix == ".csv":
            raise ValueError(
                "MUST be a CSV file! If you are looking for use JSON, use the json command"
            )

        with self.console.status("[bold white]Writing..."):
            self._bulk_inject(no_newline)
            with open(self.output, mode="w", newline="") as f:
                writer = csv.DictWriter(f, self._entries[0].get_keys())
                writer.writeheader()
                for entry in self._entries:
                    writer.writerow(entry.to_dict())
                self.console.print("[white]Done!")

    def all(self) -> list[InternalNewsEntry]:
        """Returns all entries within the extractor

        Returns:
            list[InternalNewsEntry]: List of all internal news entries
        """
        self._bulk_inject()
        return self._entries


app = ExtractorTyper()
extractor = InternalExtractor(ROOT, OUTPUT)


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
    newline: Annotated[
        bool,
        typer.Option(
            "--newline", help="Whether to include \\n characters or not", is_flag=True
        ),
    ] = False,
):
    if output:
        extractor.to_json(output, no_newline=newline)
        app.console.print("Done!")
        return
    app.console.print_json(extractor.to_json().decode())


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
    newline: Annotated[
        bool,
        typer.Option(
            "--newline", help="Whether to include \\n characters or not", is_flag=True
        ),
    ] = False,
):
    with app.console.status("[bold white]Writing..."):
        extractor.write(output, no_newline=newline)
        app.console.print(f"[white]Done! Wrote {len(extractor.all())} entries.")
