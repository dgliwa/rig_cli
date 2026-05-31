import pytest
from pathlib import Path
from rig.config.errors import FileNotFoundError_, ParseError, MissingReferenceError
from rig.config.loader import load_rig


def _write(base: Path, path: str, content: str):
    full = base / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content)


@pytest.fixture
def rig_dir(tmp_path):
    d = tmp_path / "rig"
    d.mkdir()
    _write(d, "rig.yaml", "name: test-rig\nmidi_channel: 1\n")
    _write(d, "signal-chain.yaml", "chain: []\n")
    _write(d, "pedals/brothers.yaml",
           "id: brothers\nmanufacturer: CBA\nmodel: Brothers\ntype: digital\nmidi_channel: 3\n")
    _write(d, "pedals/brothers/presets/low-gain.yaml",
           "id: low-gain\npedal: brothers\nname: Low Gain\npreset_number: 4\n")
    _write(d, "pedals/brothers/presets/lead.yaml",
           "id: lead\npedal: brothers\nname: Lead\npreset_number: 7\n")
    _write(d, "pedals/tumnus.yaml",
           "id: tumnus\nmanufacturer: Wampler\nmodel: Tumnus\ntype: analog\ncontrols:\n  - name: Gain\n    type: knob\n    min: 0\n    max: 10\n")
    _write(d, "pedals/tumnus/presets/edge.yaml",
           "id: edge\npedal: tumnus\nname: Edge of Breakup\nvalues:\n  Gain: 3.5\n")
    _write(d, "scenes/billy-clean.yaml",
           "name: billy-clean\npresets:\n  brothers: low-gain\n")
    return d


class TestLoadRig:
    def test_loads_full_config(self, rig_dir):
        config = load_rig(str(rig_dir))
        assert config.name == "test-rig"
        assert config.midi_channel == 1
        assert "brothers" in config.pedals
        assert "tumnus" in config.pedals

    def test_loads_signal_chain(self, rig_dir):
        _write(rig_dir, "signal-chain.yaml", "chain:\n  - pedal_ref: brothers\n    position: 1\n  - pedal_ref: tumnus\n    position: 2\n")
        config = load_rig(str(rig_dir))
        assert len(config.signal_chain) == 2
        assert config.signal_chain[0].pedal_ref == "brothers"

    def test_loads_presets(self, rig_dir):
        config = load_rig(str(rig_dir))
        assert len(config.digital_presets["brothers"]) == 2
        assert len(config.analog_presets["tumnus"]) == 1
        assert config.analog_presets["tumnus"][0].values["Gain"] == 3.5

    def test_loads_scenes(self, rig_dir):
        config = load_rig(str(rig_dir))
        assert "billy-clean" in config.scenes
        assert config.scenes["billy-clean"].presets["brothers"] == "low-gain"

    def test_missing_rig_yaml(self, rig_dir):
        (rig_dir / "rig.yaml").unlink()
        with pytest.raises(FileNotFoundError_):
            load_rig(str(rig_dir))

    def test_missing_signal_chain(self, rig_dir):
        (rig_dir / "signal-chain.yaml").unlink()
        with pytest.raises(FileNotFoundError_):
            load_rig(str(rig_dir))

    def test_invalid_yaml(self, rig_dir):
        _write(rig_dir, "rig.yaml", "name: test\nbroken: [\n")
        with pytest.raises(ParseError):
            load_rig(str(rig_dir))

    def test_broken_preset_reference(self, rig_dir):
        _write(rig_dir, "scenes/billy-clean.yaml",
               "name: billy-clean\npresets:\n  brothers: nonexistent-preset\n")
        with pytest.raises(MissingReferenceError):
            load_rig(str(rig_dir))

    def test_broken_pedal_reference(self, rig_dir):
        _write(rig_dir, "scenes/billy-clean.yaml",
               "name: billy-clean\npresets:\n  unknown-pedal: low-gain\n")
        with pytest.raises(MissingReferenceError):
            load_rig(str(rig_dir))

    def test_broken_signal_chain_ref(self, rig_dir):
        _write(rig_dir, "signal-chain.yaml",
               "chain:\n  - pedal_ref: unknown-pedal\n    position: 1\n")
        with pytest.raises(MissingReferenceError):
            load_rig(str(rig_dir))

    def test_scenes_dir_missing(self, rig_dir):
        # Scenes dir is optional — no scenes is valid
        import shutil
        shutil.rmtree(str(rig_dir / "scenes"))
        config = load_rig(str(rig_dir))
        assert config.scenes == {}

    def test_hx_preset_loaded_as_hx_type(self, rig_dir):
        _write(rig_dir, "pedals/hx-stomp.yaml",
               "id: hx-stomp\nmanufacturer: Line6\nmodel: HX Stomp\ntype: modeler\nmidi_channel: 1\n")
        _write(rig_dir, "pedals/hx-stomp/presets/clean.yaml",
               "id: clean\npedal: hx-stomp\nname: Clean Edge\npreset_number: 12\nblocks:\n  - name: Amp\n    type: amp\n    model: US Double Nrm\n    settings:\n      Drive: 4.5\n")
        config = load_rig(str(rig_dir))
        assert len(config.hx_presets["hx-stomp"]) == 1
        assert config.hx_presets["hx-stomp"][0].blocks[0].settings["Drive"] == 4.5
