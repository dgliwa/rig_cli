import json

from rig.engine.diff import compute_diff, format_diff
from rig.models.device import Device, DeviceType
from rig.models.preset import DigitalPreset, HXStompPreset
from rig.models.rig import Rig
from rig.models.scene import Scene
from rig_chasebliss.device import ChaseBlissConfig


def _make_rig() -> Rig:
    hx = Device(
        id="hx-stomp",
        manufacturer="Line6",
        model="HX Stomp",
        type=DeviceType.MODELER,
        config={"type": "midi", "midi_channel": 1},
        presets=[
            HXStompPreset(
                id="clean-edge",
                name="Clean Edge",
                preset_number=12,
                hlx_file="hlx/clean-edge.hlx",
            )
        ],
    )
    bro = Device(
        id="brothers",
        manufacturer="CBA",
        model="Brothers",
        type=DeviceType.DIGITAL,
        config=ChaseBlissConfig(midi_channel=3),
        presets=[DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain", preset_number=4)],
    )
    ctrl = Device(
        id="mc6",
        manufacturer="Morningstar",
        model="MC6",
        type=DeviceType.CONTROLLER,
        config={"type": "controller", "midi_channel": 1, "banks": []},
    )
    scene = Scene(
        name="test-scene",
        presets={"hx-stomp": "clean-edge", "brothers": "low-gain"},
    )
    return Rig(
        name="test",
        signal_chain=["hx-stomp"],
        devices={"hx-stomp": hx, "brothers": bro, "mc6": ctrl},
        scenes={"test-scene": scene},
    )


class TestDiff:
    def test_diff_detects_new_scene(self, tmp_path):
        rig = _make_rig()
        diff = compute_diff(rig, root_path=str(tmp_path))
        assert "test-scene" in diff["scenes"]
        assert diff["scenes"]["test-scene"]["_status"] == "new"

    def test_diff_clean_when_state_matches(self, tmp_path):
        rig = _make_rig()
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(
            json.dumps(
                {
                    "devices": {
                        "hx-stomp": {"last_preset": "clean-edge"},
                        "brothers": {"last_preset": "low-gain"},
                    },
                    "scenes": {"test-scene": {}},
                }
            )
        )
        diff = compute_diff(rig, root_path=str(tmp_path))
        assert "test-scene" not in diff["scenes"]

    def test_diff_detects_preset_change(self, tmp_path):
        rig = _make_rig()
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(
            json.dumps(
                {
                    "devices": {
                        "hx-stomp": {"last_preset": "old-preset"},
                        "brothers": {"last_preset": "low-gain"},
                    },
                    "scenes": {"test-scene": {}},
                }
            )
        )
        diff = compute_diff(rig, root_path=str(tmp_path))
        assert diff["scenes"]["test-scene"]["presets"]["hx-stomp"]["old"] == "old-preset"

    def test_format_diff_includes_arrow(self):
        diff = {
            "scenes": {
                "test-scene": {
                    "_status": "changed",
                    "presets": {"hx-stomp": {"_status": "changed", "old": "old", "new": "new"}},
                },
            },
        }
        output = format_diff(diff)
        assert "→" in output
        assert "test-scene" in output

    def test_format_diff_new_scene(self):
        diff = {
            "scenes": {
                "test-scene": {
                    "_status": "new",
                    "presets": {"hx-stomp": {"_status": "added", "new": "clean-edge"}},
                },
            },
        }
        output = format_diff(diff)
        assert "[new]" in output
        assert "'clean-edge'" in output
