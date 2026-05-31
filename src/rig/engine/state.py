import json
from pathlib import Path
from typing import Any


def read_state(root: str) -> dict[str, Any]:
    path = Path(root) / ".rig" / "state.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def write_state(root: str, state: dict[str, Any]):
    path = Path(root) / ".rig" / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)
