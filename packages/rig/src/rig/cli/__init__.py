from rig.cli._shared import app

# Import command modules to trigger @app.command() registration
from rig.cli.commands import apply, diff, edit, plan, status, validate  # noqa: F401

__all__ = ["app"]
