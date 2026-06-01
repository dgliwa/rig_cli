from __future__ import annotations

import logging

from rich.console import Console
from rich.logging import RichHandler

_RIG_LOGGER_NAME = "rig"
_LOGGER = logging.getLogger(_RIG_LOGGER_NAME)
_HANDLER_ATTR = "_rig_handler"


def setup_logging(verbose: int = 0) -> None:
    """Configure the root rig logger based on verbosity count.

    Verbosity levels:
        0 (no -v):  WARNING and above
        1 (-v):     INFO and above
        2+ (-vv):   DEBUG and above

    Logs are sent to stderr via RichHandler so they never interfere
    with stdout output (important for --format json).
    """
    level = logging.WARNING
    if verbose >= 2:
        level = logging.DEBUG
    elif verbose >= 1:
        level = logging.INFO

    _LOGGER.setLevel(level)

    # Clean any existing rig handlers so re-entrant calls are safe
    for handler in list(_LOGGER.handlers):
        if getattr(handler, _HANDLER_ATTR, False):
            _LOGGER.removeHandler(handler)

    console = Console(stderr=True)
    handler = RichHandler(
        console=console,
        show_path=False,
        rich_tracebacks=True,
    )
    setattr(handler, _HANDLER_ATTR, True)
    handler.setLevel(level)

    formatter = logging.Formatter("%(name)s: %(message)s")
    handler.setFormatter(formatter)

    _LOGGER.addHandler(handler)

    # Prevent propagation to root logger (avoid double output)
    _LOGGER.propagate = False
