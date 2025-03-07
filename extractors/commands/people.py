import csv
from pathlib import Path
from typing import Annotated, Any, Optional

import msgspec
import typer
from rich.console import Console
from rich.tree import Tree
from yarl import URL

from core import ROOT, ExtractorTyper

__description__ = "Commands to extract and write information from the Peoples page"


class Entry(msgspec.Struct, frozen=True):
    id: str
    name: str
    title: str
    image: URL
    affiliation: Optional[str] = None
    link: Optional[URL] = None

    def to_keys(self) -> list[str]:
        return [f for f in self.__struct_fields__]

    def to_dict(self):
        return {f: getattr(self, f) for f in self.__struct_fields__}


class PeopleExtractor:
    def __init__(self, root: Path):
        self.root = root
        self.console = Console()

        self._csv_file = self.root / "people.csv"

        self._encoder = msgspec.json.Encoder(enc_hook=self._enc_hook)

        self._entries: list[Entry] = []
        self._load()

    def _enc_hook(self, obj: Any) -> Any:
        if isinstance(obj, URL):
            return str(obj)
        return obj

    def _load(self):
        try:
            with open(self._csv_file, "r") as f:
                self._entries = [
                    Entry(
                        affiliation=entry["Affiliation"] or None,
                        link=URL(entry["LINK"]),
                        image=URL.build(
                            scheme="https",
                            host="citris.ucmerced.edu",
                            path=f"/images/people/{entry['ID']}.jpg",
                        ),
                        **{
                            k.lower(): v
                            for k, v in entry.items()
                            if k and k not in ("Affiliation", "LINK")
                        },
                    )
                    for entry in csv.DictReader(f, delimiter=",")
                    if entry["ID"] != "HEADER"
                ]
        except FileNotFoundError:
            self._entries = []

    def to_json(self, output: Optional[Path] = None):
        """Writes/outputs entries in JSON format

        Args:
            output (Path): Output path. Defaults to None, which will pipe to stdout

        Returns:
            bytes: Returns the encoded entries in JSON format
        """
        encoded = self._encoder.encode(self._entries)
        if output:
            output.write_bytes(encoded)

        return encoded

    def to_csv(self, output: Path):
        """Public entrypoint to start writing all information down

        Args:
            output (Path): Output path. MUST be a csv fie

        Raises:
            ValueError: The file extension is not a CSV
        """
        if not output.suffix == ".csv":
            raise ValueError("MUST be a CSV file!")

        with open(output, mode="w") as f:
            writer = csv.DictWriter(f, self._entries[0].to_keys())
            writer.writeheader()

            for entry in self._entries:
                writer.writerow(entry.to_dict())

    def display(self) -> None:
        """Display extracted and sorted content via a tree-based format"""
        tree = Tree("[bold white]CITRIS @ UC Merced People")
        for entry in self._entries:
            file_tree = tree.add(entry.name)
            file_tree.add(f"TITLE: {entry.title}")
            file_tree.add(f"AFFILIATION: {entry.affiliation or None}")
            file_tree.add(f"EXTERNAL LINK: {entry.link or None}")
            file_tree.add(f"IMAGE URL: {entry.image}")

        self.console.print(tree)

    def all(self) -> list[Entry]:
        """Provides all of the entries in a public manner"""
        return self._entries


app = ExtractorTyper()
extractor = PeopleExtractor(ROOT)


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
    """Write or display JSON-formatted extracted data"""
    if output:
        extractor.to_json(output)
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
    ] = ROOT / "debug" / "citris-people.csv",
):
    """Write the extracted data into a CSV file"""

    if output.suffix != ".csv":
        raise ValueError("Requested output MUST be a .csv file")

    with app.console.status("[bold white]Writing..."):
        extractor.to_csv(output)
        app.console.print(f"[white]Done! Wrote {len(extractor.all())} entries.")


@app.command(name="display")
def display() -> None:
    """Display extracted entries in a tree-like format or markdown in lists"""
    extractor.display()
