# This complete CLI script is designed to extract images from news files, display, store, and download them all.
# Make sure to create an virtualenv ("python3 -m venv .venv"), activate it, and install all of the requirements. ("pip install -r extractors/requirements.txt")
# This script heavily depends on external libraries, and also depend heavily on C/Cython based libraries (e.g., aiohttp, aiofile, yarl, lxml, and msgspec).
# Run "python extractors/main.py --help" to get started with usage.

from commands import app_commands
from core import ExtractorTyper

app = ExtractorTyper()
app.add_typer(app_commands)

if __name__ == "__main__":
    app()
