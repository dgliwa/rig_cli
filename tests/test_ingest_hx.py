import json
import zipfile
from pathlib import Path

from rig.ingest.hx_stomp import ingest_hx_file
from rig.models.preset import HXStompPreset


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
        ],
    }
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("preset.json", json.dumps(preset_data))
    return path


class TestIngestHx:
    def test_ingest_hlx_extracts_preset(self, tmp_path):
        hlx_path = _make_test_hlx(tmp_path / "test.hlx")
        presets = ingest_hx_file(str(hlx_path))
        assert len(presets) == 1
        assert presets[0].name == "Clean Edge"

    def test_ingest_hlx_model_type(self, tmp_path):
        hlx_path = _make_test_hlx(tmp_path / "test.hlx")
        presets = ingest_hx_file(str(hlx_path))
        assert isinstance(presets[0], HXStompPreset)
        assert presets[0].id == "clean-edge"
        assert presets[0].preset_number == 0

    def test_ingest_hlx_stores_absolute_hlx_file(self, tmp_path):
        hlx_path = _make_test_hlx(tmp_path / "test.hlx")
        presets = ingest_hx_file(str(hlx_path))
        assert presets[0].hlx_file == str(hlx_path.resolve())

    def test_ingest_hlx_stores_relative_hlx_file_when_repo_root_given(self, tmp_path):
        hlx_dir = tmp_path / "hlx"
        hlx_dir.mkdir()
        hlx_path = _make_test_hlx(hlx_dir / "test.hlx")
        presets = ingest_hx_file(str(hlx_path), repo_root=str(tmp_path))
        assert presets[0].hlx_file == "hlx/test.hlx"

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
