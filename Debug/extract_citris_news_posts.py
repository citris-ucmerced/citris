import csv
import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote

import msgspec
from bs4 import BeautifulSoup
from dateutil.parser import parse
from rich.console import Console
from yarl import URL

ROOT = Path(__file__).parents[1]
OUTPUT = Path(__file__).parent / "news-wp-exporter.csv"


class NewsEntry(msgspec.Struct):
    id: str
    title: str
    link: str
    date: datetime.datetime
    description: str
    content: Optional[str] = None
    imagesize: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {f: getattr(self, f) for f in self.__struct_fields__}

    def get_keys(self) -> list[str]:
        return [f for f in self.__struct_fields__]


class Extractor:
    def __init__(self, root: Path, output: Path):
        self.root = root
        self.output = output
        self.console = Console()
        self._csv_file = self.root / "news.csv"
        self._encoder = msgspec.json.Encoder()

        # This is a list as we have multiple rows within our csv file.
        # We are guaranteed to have multiple. If's it just one, then it just a dict
        self._db: list[NewsEntry] = []
        self._load_from_file()

    def _load_from_file(self) -> None:
        try:
            with open(self._csv_file, "r") as f:
                self._db: list[NewsEntry] = [
                    NewsEntry(
                        date=parse(entry["DATE"]),
                        **{k.lower(): v for k, v in entry.items() if not k == "DATE"},
                    )
                    for entry in csv.DictReader(f, delimiter=",")
                    if entry["LINK"].startswith("https://citris.ucmerced.edu/news")
                ]
        except FileNotFoundError:
            self._db = []

    def _bulk_inject(self, no_newline: bool = False) -> list[NewsEntry]:
        for entry in self._db:
            entry.content = (
                self.extract_html(entry).replace("\n", "")
                if no_newline
                else self.extract_html(entry)
            )
        return self._db

    def extract_html(self, entry: NewsEntry, section_only: bool = True) -> str:
        """Parses and extracts HTML news files and outputs the text of the file.

        Args:
            entry (NewsEntry): NewsEntry instance
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

    def to_json(self) -> bytes:
        """Takes the extracted and converted entries and output as a JSON-valid output

        Returns:
            bytes: JSON-encoded data
        """
        return self._encoder.encode(self._db)

    def write(self, no_newline: bool = False) -> None:
        """Public entrypoint to start extracting, parsing, and writing the content to the CSV file defined.

        Args:
            no_newline: Whether to strip all `\n` characters out from parsed HTML content. Defaults to False
        """
        with self.console.status("[bold white]Writing..."):
            self._bulk_inject(no_newline)

            with open(self.output, mode="w", newline="") as f:
                writer = csv.DictWriter(f, self._db[0].get_keys())
                writer.writeheader()
                for entry in self._db:
                    writer.writerow(entry.to_dict())

            self.console.print("[white]Done!")


if __name__ == "__main__":
    extractor = Extractor(ROOT, OUTPUT)
    extractor.write(no_newline=True)
