"""Root Typer application for ELIMS command groups."""

import typer

from .boards import app as boards_app
from .database import app as database_app
from .duts import app as duts_app
from .instruments import app as instruments_app

app = typer.Typer(
    name="elims",
    help="ELIMS laboratory command-line tools.",
    no_args_is_help=True,
)
app.add_typer(instruments_app, name="instruments")
app.add_typer(boards_app, name="boards")
app.add_typer(duts_app, name="duts")
app.add_typer(database_app, name="database")
