from pathlib import Path

import pytest

from rig.config.errors import FileNotFoundError_, MissingReferenceError, ParseError
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
    _write(
        d,
        "pedals/brothers.yaml",
        "id: brothers\nmanufacturer: CBA\nmodel: Brothers\ntype: digital\nconfig: {type: midi, midi_channel: 3}\n",
    )
    _write(
        d,
        "pedals/brothers/presets/low-gain.yaml",
        "id: low-gain\npedal: brothers\nname: Low Gain\npreset_number: 4\n",
    )
    _write(
        d,
        "pedals/brothers/presets/lead.yaml",
        "id: lead\npedal: brothers\nname: Lead\npreset_number: 7\n",
    )
    _write(
        d,
        "pedals/tumnus.yaml",
        "id: tumnus\nmanufacturer: Wampler\nmodel: Tumnus\ntype: analog\nconfig:\n  type: manual\n  controls:\n    - name: Gain\n      type: knob\n      min: 0\n      max: 10\n",
    )
    _write(
        d,
        "pedals/tumnus/presets/edge.yaml",
        "id: edge\npedal: tumnus\nname: Edge of Breakup\nvalues:\n  Gain: 3.5\n",
    )
    # Controller device: scenes are wired to ControllerConfig by the loader
    _write(
        d,
        "pedals/mc6.yaml",
        "id: mc6\nmanufacturer: Morningstar\nmodel: MC6\ntype: controller\nconfig:\n  type: controller\n  midi_channel: 1\n  banks: []\n",
    )
    _write(d, "scenes/billy-clean.yaml", "name: billy-clean\npresets:\n  brothers: low-gain\n")
    return d


class TestLoadRig:
    def test_loads_full_config(self, rig_dir):
        config = load_rig(str(rig_dir))
        assert config.name == "test-rig"
        assert config.midi_channel == 1
        assert "brothers" in config.devices
        assert "tumnus" in config.devices

    def test_loads_signal_chain(self, rig_dir):
        _write(
            rig_dir,
            "signal-chain.yaml",
            "chain:\n  - pedal: brothers\n    position: 1\n  - pedal: tumnus\n    position: 2\n",
        )
        config = load_rig(str(rig_dir))
        assert len(config.signal_chain) == 2
        assert config.signal_chain[0].device_ref == "brothers"

    def test_loads_presets(self, rig_dir):
        config = load_rig(str(rig_dir))
        brothers = config.devices["brothers"]
        tumnus = config.devices["tumnus"]
        digital_presets = [p for p in brothers.presets]
        analog_presets = [p for p in tumnus.presets]
        assert len(digital_presets) == 2
        assert len(analog_presets) == 1
        assert analog_presets[0].values["Gain"] == 3.5

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
        _write(
            rig_dir,
            "scenes/billy-clean.yaml",
            "name: billy-clean\npresets:\n  brothers: nonexistent-preset\n",
        )
        with pytest.raises(MissingReferenceError):
            load_rig(str(rig_dir))

    def test_broken_pedal_reference(self, rig_dir):
        _write(
            rig_dir,
            "scenes/billy-clean.yaml",
            "name: billy-clean\npresets:\n  unknown-pedal: low-gain\n",
        )
        with pytest.raises(MissingReferenceError):
            load_rig(str(rig_dir))

    def test_broken_signal_chain_ref(self, rig_dir):
        _write(
            rig_dir,
            "signal-chain.yaml",
            "chain:\n  - pedal: unknown-device\n    position: 1\n",
        )
        with pytest.raises(MissingReferenceError):
            load_rig(str(rig_dir))

    def test_scenes_dir_missing(self, rig_dir):
        import shutil

        shutil.rmtree(str(rig_dir / "scenes"))
        config = load_rig(str(rig_dir))
        assert config.scenes == {}

    def test_cba_pedal_without_midi_channel_rejected(self, rig_dir):
        from pydantic import ValidationError

        _write(
            rig_dir,
            "pedals/brothers.yaml",
            "id: brothers\nmanufacturer: Chase Bliss\nmodel: Brothers\ntype: digital\nconfig: {type: chase_bliss}\n",
        )
        with pytest.raises(ValidationError, match="midi_channel"):
            load_rig(str(rig_dir))

    def test_non_cba_pedal_without_midi_channel_accepted(self, rig_dir):
        _write(
            rig_dir,
            "pedals/brothers.yaml",
            "id: brothers\nmanufacturer: Some Brand\nmodel: Thing\ntype: digital\nconfig: {type: midi, midi_channel: 1}\n",
        )
        config = load_rig(str(rig_dir))
        assert "brothers" in config.devices

    def test_hx_preset_loaded_as_hx_type(self, rig_dir):
        from rig.models.preset import HXStompPreset

        _write(
            rig_dir,
            "pedals/hx-stomp.yaml",
            "id: hx-stomp\nmanufacturer: Line6\nmodel: HX Stomp\ntype: modeler\nconfig: {type: midi, midi_channel: 1}\n",
        )
        _write(
            rig_dir,
            "pedals/hx-stomp/presets/clean.yaml",
            "id: clean\nname: Clean Edge\npreset_number: 12\nhlx_file: hlx/clean-edge.hlx\n",
        )
        config = load_rig(str(rig_dir))
        hx_presets = [p for p in config.devices["hx-stomp"].presets if isinstance(p, HXStompPreset)]
        assert len(hx_presets) == 1
        assert hx_presets[0].preset_number == 12
        assert hx_presets[0].hlx_file == "hlx/clean-edge.hlx"

    def test_loads_controller_as_device(self, rig_dir):
        from rig.models.device import DeviceType

        config = load_rig(str(rig_dir))
        assert "mc6" in config.devices
        assert config.devices["mc6"].type == DeviceType.CONTROLLER
        assert config.controller is not None
        assert config.controller.id == "mc6"

    def test_scenes_accessible_via_controller(self, rig_dir):
        config = load_rig(str(rig_dir))
        assert "billy-clean" in config.scenes
