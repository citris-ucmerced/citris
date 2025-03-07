import csv
from pathlib import Path
from typing import Any, Optional

import msgspec
from rich.console import Console
from yarl import URL

ROOT = Path(__file__).parents[2]


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


class Header(msgspec.Struct, frozen=True):
    id: str
    name: str


class PeopleExtractor:
    def __init__(self, root: Path, *, exclude_header: bool = False):
        self.root = root
        self.exclude_header = exclude_header
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
        encoded = self._encoder.encode(self._entries)
        if output:
            output.write_bytes(encoded)

        return encoded

    def to_csv(self, output: Path):
        if not output.suffix == ".csv":
            raise ValueError("MUST be a CSV file!")

        with open(output, mode="w") as f:
            writer = csv.DictWriter(f, self._entries[0].to_keys())
            writer.writeheader()

            for entry in self._entries:
                writer.writerow(entry.to_dict())


extractor = PeopleExtractor(ROOT, exclude_header=True)
extractor.to_csv(ROOT / "debug" / "people-data.csv")
