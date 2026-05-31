import json
import zipfile
from pathlib import Path
from rig.ingest.hx_stomp import ingest_hx_file


def _make_test_hlx(path: Path) -> Path:
    """Create a minimal .hlx file (zip with preset JSON)."""
    preset_data = {
        "meta": {"name": "Clean Edge"},
        "chain": [
            {
                "name": "Amp",
                "type": "amp",
                "model": "US Double Nrm",
                "enabled": True,
                "parameters": {"Drive": 4.5, "Bass": 5.0},
            },
            {
                "name": "Cab",
                "type": "cab",
                "model": "4x12 Greenback 25",
                "enabled": True,
                "parameters": {},
            },
        ],
    }
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("preset.json", json.dumps(preset_data))
    return path


class TestIngestHx:
    def test_ingest_hlx_extracts_presets(self, tmp_path):
        hlx_path = _make_test_hlx(tmp_path / "test.hlx")
        presets = ingest_hx_file(str(hlx_path))
        assert len(presets) == 1
        assert presets[0]["name"] == "Clean Edge"
        assert len(presets[0]["blocks"]) == 2

    def test_ingest_hlx_parses_blocks(self, tmp_path):
        hlx_path = _make_test_hlx(tmp_path / "test.hlx")
        presets = ingest_hx_file(str(hlx_path))
        block = presets[0]["blocks"][0]
        assert block["name"] == "Amp"
        assert block["type"] == "amp"
        assert block["settings"]["Drive"] == 4.5

    def test_ingest_hlx_missing_file(self):
        try:
            ingest_hx_file("/nonexistent/file.hlx")
            assert False, "Expected FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_ingest_hlx_empty_zip(self, tmp_path):
        path = tmp_path / "empty.hlx"
        with zipfile.ZipFile(path, "w"):
            pass
        presets = ingest_hx_file(str(path))
        assert presets == []
