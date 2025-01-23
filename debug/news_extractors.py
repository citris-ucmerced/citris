# Complete CLI program for extracting information from all news posts

import csv
import datetime
from pathlib import Path
from typing import Annotated, Any, Optional

import msgspec
import typer
from dateutil.parser import parse
from rich.console import Console
from yarl import URL

__title__ = "News Extractor"
__help_description__ = "Extractor for both internal and external news posts"

ROOT = Path(__file__).parents[1]


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
                    if not entry["LINK"].startswith("https://citris.ucmerced.edu/news")
                ]
        except FileNotFoundError:
            self._entries = []

    def all(self) -> list[ExternalNewsEntry]:
        return self._entries

    def to_json(self, output: Optional[Path] = None) -> bytes:
        """Writes/outputs entries in JSON format

        Args:
            output (Path): Output path

        Returns:
            bytes: Returns the encoded entries in JSON format
        """
        encoded = self._encoder.encode(self._entries)
        if output:
            output.write_bytes(encoded)
        return encoded

    def write(self, output: Path) -> None:
        """Public entrypoint to start writing all information down

        Args:
            output (Path): Output path. MUST be a csv fie

        Raises:
            ValueError: The file extension is not a CSV
        """
        if not output.suffix == ".csv":
            raise ValueError(
                "MUST be a CSV file! If you are looking for use JSON, use the json command"
            )

        with open(output, mode="w") as f:
            writer = csv.DictWriter(f, self._entries[0].get_keys())
            writer.writeheader()
            for entry in self._entries:
                writer.writerow(entry.to_dict())


class ImageExtractorTyper(typer.Typer):
    def __init__(self, *args, **kwargs):
        super().__init__(
            help=__help_description__, add_completion=False, *args, **kwargs
        )
        self.console = Console()
        self.external_extractor = ExternalExtractor(ROOT)


app = ImageExtractorTyper()


@app.command(name="external-json")
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
    if output:
        app.external_extractor.to_json(output)
        app.console.print("Done!")
        return
    app.console.print_json(app.external_extractor.to_json().decode())


@app.command(name="external-write")
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
):
    with app.console.status("[bold white]Writing..."):
        app.external_extractor.write(output)
        app.console.print(
            f"[white]Done! Wrote {len(app.external_extractor.all())} entries."
        )


if __name__ == "__main__":
    app()
