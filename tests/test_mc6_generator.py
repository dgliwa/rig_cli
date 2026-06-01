import json

from rig.generators.mc6_presets import generate_mc6, write_mc6_config
from rig.models.pedal import MidiConfig, PedalDefinition, PedalType
from rig.models.preset import HXStompPreset
from rig.models.rig import RigConfig
from rig.models.scene import Scene
from rig.models.signal_chain import SignalChainPosition


def _make_rig() -> RigConfig:
    hx = PedalDefinition(
        id="hx-stomp",
        manufacturer="Line6",
        model="HX Stomp",
        type=PedalType.MODELER,
        config=MidiConfig(midi_channel=1),
    )
    return RigConfig(
        name="test",
        signal_chain=[SignalChainPosition(pedal_ref="hx-stomp", position=1)],
        pedals={"hx-stomp": hx},
        hx_presets={
            "hx-stomp": [
                HXStompPreset(
                    id="clean-edge",
                    name="Clean Edge",
                    preset_number=12,
                    hlx_file="hlx/clean-edge.hlx",
                ),
                HXStompPreset(id="lead", name="Lead", preset_number=5, hlx_file="hlx/lead.hlx"),
            ],
        },
        scenes={
            "billy-clean": Scene(name="billy-clean", presets={"hx-stomp": "clean-edge"}),
            "lead": Scene(name="lead", presets={"hx-stomp": "lead"}),
        },
        mc6={
            "banks": [
                {
                    "bank": 1,
                    "name": "Scenes",
                    "switches": {
                        "A": {"scene": "billy-clean"},
                        "B": {"scene": "lead"},
                        "C": {"scene": "nonexistent"},
                    },
                },
            ],
        },
    )


class TestMc6Generator:
    def test_generates_bank_with_pc_commands(self):
        data = generate_mc6(_make_rig())
        assert "bank1" in data
        assert data["bank1"]["name"] == "Scenes"
        switch_a = data["bank1"]["presets"]["A"]
        assert switch_a["name"] == "billy-clean"
        assert len(switch_a["commands"]) == 1
        assert switch_a["commands"][0]["type"] == "pc"
        assert switch_a["commands"][0]["value"] == 12

    def test_generates_multiple_switches(self):
        data = generate_mc6(_make_rig())
        assert len(data["bank1"]["presets"]) == 3
        assert data["bank1"]["presets"]["B"]["commands"][0]["value"] == 5

    def test_nonexistent_scene_has_empty_commands(self):
        data = generate_mc6(_make_rig())
        assert data["bank1"]["presets"]["C"]["commands"] == []

    def test_write_mc6_config_creates_files(self, tmp_path):
        data = generate_mc6(_make_rig())
        write_mc6_config(data, output_path=str(tmp_path / "mc6"))
        assert (tmp_path / "mc6" / "bank1.json").exists()
        with open(tmp_path / "mc6" / "bank1.json") as f:
            parsed = json.load(f)
            assert parsed["presets"]["A"]["commands"][0]["value"] == 12

    def test_no_mc6_config_returns_empty(self):
        rig = _make_rig()
        rig.mc6 = {}
        data = generate_mc6(rig)
        assert data == {}
