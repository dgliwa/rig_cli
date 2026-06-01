import json
import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


def read_state(root: str) -> dict[str, Any]:
    path = Path(root) / ".rig" / "state.json"
    if not path.exists():
        logger.debug("No state file at %s", path)
        return {}
    logger.debug("Reading state from %s", path)
    with open(path) as f:
        data = json.load(f)
    logger.debug("Loaded state: %d device(s), %d scene(s)",
                 len(data.get("devices", {})), len(data.get("scenes", {})))
    return data


def write_state(root: str, state: dict[str, Any]):
    path = Path(root) / ".rig" / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug("Writing state to %s (%d devices, %d scenes)",
                 path, len(state.get("devices", {})), len(state.get("scenes", {})))
    with open(path, "w") as f:
        json.dump(state, f, indent=2)
