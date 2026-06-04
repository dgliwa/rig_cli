from rig.cli._shared import app, gen_app

# Import command modules to trigger @app.command() / @gen_app.command() registration
from rig.cli.commands import apply, diff, generate, plan, status, validate  # noqa: F401

app.add_typer(gen_app, name="generate")

__all__ = ["app"]
