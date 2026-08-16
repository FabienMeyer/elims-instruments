"""Root Typer application for ELIMS command groups."""

import typer

from .instruments import app as instruments_app
from .boards import app as boards_app

app = typer.Typer(
    name="elims",
    help="ELIMS laboratory command-line tools.",
    no_args_is_help=True,
)
app.add_typer(instruments_app, name="instruments")
app.add_typer(boards_app, name="boards")
