import json
from pathlib import Path
from rig.ingest.mc6_config import ingest_mc6_config


def _make_mc6_config(path: Path):
    data = {
        "bank1": {
            "name": "Scenes",
            "presets": {
                "A": {
                    "name": "Billy Clean",
                    "commands": [{"type": "pc", "channel": 1, "value": 12}],
                },
                "B": {
                    "name": "Crunch",
                    "commands": [{"type": "pc", "channel": 1, "value": 7}],
                },
            },
        },
        "bank2": {
            "name": "More",
            "presets": {
                "A": {
                    "name": "Lead",
                    "commands": [{"type": "pc", "channel": 1, "value": 5}],
                },
            },
        },
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


class TestIngestMc6:
    def test_ingest_mc6_creates_scenes(self, tmp_path):
        mc6_path = _make_mc6_config(tmp_path / "mc6.json")
        scenes = ingest_mc6_config(str(mc6_path))
        assert len(scenes) == 3

    def test_ingest_mc6_maps_bank_and_switch(self, tmp_path):
        mc6_path = _make_mc6_config(tmp_path / "mc6.json")
        scenes = ingest_mc6_config(str(mc6_path))
        scene_a = [s for s in scenes if s["mc6_switch"] == "A" and s["mc6_bank"] == 1][0]
        assert scene_a["mc6_bank"] == 1
        assert scene_a["mc6_switch"] == "A"

    def test_ingest_mc6_maps_pc_commands(self, tmp_path):
        mc6_path = _make_mc6_config(tmp_path / "mc6.json")
        scenes = ingest_mc6_config(str(mc6_path))
        scene_b = [s for s in scenes if s["mc6_switch"] == "B"][0]
        assert "unknown-ch1" in scene_b["presets"]
        assert scene_b["presets"]["unknown-ch1"] == "pc7"

    def test_ingest_mc6_missing_file(self):
        try:
            ingest_mc6_config("/nonexistent/config.json")
            assert False, "Expected FileNotFoundError"
        except FileNotFoundError:
            pass
