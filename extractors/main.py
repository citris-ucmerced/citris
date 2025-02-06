from commands import app_commands
from core import ExtractorTyper

app = ExtractorTyper()
app.add_typer(app_commands)

if __name__ == "__main__":
    app()
