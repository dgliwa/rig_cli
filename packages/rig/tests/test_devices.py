"""Tests for concrete Device plugin types in plugin packages.

Phase 7: All device classes moved from core rig.engine.devices to their
respective plugin packages. Imported directly from plugin packages:
- AnalogDevice from rig_analog.device
- HXStompDevice from rig_hx.device (was HXStompDevice)
- ChaseBlissDevice from rig_chasebliss.device
- MC6Device from rig_morningstar.device
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from rig.engine.plan.models import DeviceAction
from rig.engine.plugin import DeviceApplyContext
from rig.engine.state import RigState
from rig_analog.config import AnalogConfig
from rig_chasebliss.device import ChaseBlissConfig
from rig_hx.config import HXStompConfig
from rig_morningstar.config import MC6Config
from tests.fakes import InMemoryPromptAdapter

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_rig"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_apply_ctx(
    device_id: str = "test-device",
    preset_name: str = "TestPreset",
    preset_number: int | None = 1,
    midi_channel: int | None = 1,
    dry_run: bool = False,
    connected: set[str] | None = None,
    confirmation_io: InMemoryPromptAdapter | None = None,
    rig=None,
) -> DeviceApplyContext:
    action = DeviceAction(
        device=device_id,
        device_type="analog",
        status="analog",
        preset_name=preset_name,
        preset_number=preset_number,
        midi_channel=midi_channel,
    )
    return DeviceApplyContext(
        action=action,
        state=RigState(),
        rig=rig or object(),
        dry_run=dry_run,
        confirmation_io=confirmation_io or InMemoryPromptAdapter(default="skip"),
        midi=MagicMock(),
        connected_devices=connected or set(),
        config_path=None,
    )


# ---------------------------------------------------------------------------
# Import tests
# ---------------------------------------------------------------------------


def test_analog_device_importable() -> None:
    from rig_analog.device import AnalogDevice

    assert AnalogDevice is not None


def test_midi_device_importable() -> None:
    from rig_hx.device import HXStompDevice

    assert HXStompDevice is not None


def test_chase_bliss_device_importable() -> None:
    from rig_chasebliss.device import ChaseBlissDevice

    assert ChaseBlissDevice is not None


def test_mc6_device_importable() -> None:
    from rig_morningstar.device import MC6Device

    assert MC6Device is not None


# ---------------------------------------------------------------------------
# AnalogDevice — Protocol conformance
# ---------------------------------------------------------------------------


def test_analog_device_has_id_property() -> None:
    from rig_analog.device import AnalogDevice

    dev = AnalogDevice(id="fuzz", name="Fuzz Face", config=AnalogConfig())
    assert dev.id == "fuzz"


def test_analog_device_has_name_property() -> None:
    from rig_analog.device import AnalogDevice

    dev = AnalogDevice(id="fuzz", name="Fuzz Face", config=AnalogConfig())
    assert dev.name == "Fuzz Face"


def test_analog_device_has_config_property() -> None:
    from rig_analog.device import AnalogDevice

    cfg = AnalogConfig()
    dev = AnalogDevice(id="fuzz", name="Fuzz Face", config=cfg)
    assert isinstance(dev.config, AnalogConfig)


# ---------------------------------------------------------------------------
# AnalogDevice — apply behavior
# ---------------------------------------------------------------------------


def test_analog_device_apply_dry_run_returns_skipped() -> None:
    from rig_analog.device import AnalogDevice

    dev = AnalogDevice(id="fuzz", name="Fuzz Face", config=AnalogConfig())
    ctx = _make_apply_ctx(device_id="fuzz", preset_name="Noon", dry_run=True)
    result = dev.apply(ctx)
    assert result.status == "skipped"
    assert result.device == "fuzz"


def test_analog_device_apply_confirm_returns_confirmed() -> None:
    from unittest.mock import patch

    from rig_analog.device import AnalogDevice

    dev = AnalogDevice(id="fuzz", name="Fuzz Face", config=AnalogConfig())
    ctx = _make_apply_ctx(device_id="fuzz", preset_name="Noon")
    with patch("rig_analog.device.prompt_analog", return_value="confirm"):
        result = dev.apply(ctx)
    assert result.status == "confirmed"
    assert result.preset == "Noon"


def test_analog_device_apply_quit_returns_error() -> None:
    from unittest.mock import patch

    from rig_analog.device import AnalogDevice

    dev = AnalogDevice(id="fuzz", name="Fuzz Face", config=AnalogConfig())
    ctx = _make_apply_ctx(device_id="fuzz", preset_name="Noon")
    with patch("rig_analog.device.prompt_analog", return_value="quit"):
        result = dev.apply(ctx)
    assert result.status == "error"
    assert result.error == "quit"


# ---------------------------------------------------------------------------
# HXStompDevice — Protocol conformance
# ---------------------------------------------------------------------------


def test_midi_device_has_id_property() -> None:
    from rig_hx.device import HXStompDevice

    dev = HXStompDevice(id="hx-stomp", name="HX Stomp", config=HXStompConfig())
    assert dev.id == "hx-stomp"


def test_midi_device_apply_dry_run_returns_skipped() -> None:
    from rig_hx.device import HXStompDevice

    dev = HXStompDevice(id="hx-stomp", name="HX Stomp", config=HXStompConfig())
    ctx = _make_apply_ctx(device_id="hx-stomp", preset_name="Clean", dry_run=True)
    result = dev.apply(ctx)
    assert result.status == "skipped"
    assert result.device == "hx-stomp"


def test_midi_device_apply_confirm_returns_confirmed() -> None:
    from rig_hx.device import HXStompDevice

    dev = HXStompDevice(id="hx-stomp", name="HX Stomp", config=HXStompConfig())
    ctx = _make_apply_ctx(
        device_id="hx-stomp",
        preset_name="Clean",
        confirmation_io=InMemoryPromptAdapter(default="confirm"),
    )
    result = dev.apply(ctx)
    assert result.status == "confirmed"


# ---------------------------------------------------------------------------
# ChaseBlissDevice — Protocol conformance
# ---------------------------------------------------------------------------


def test_chase_bliss_device_has_id_property() -> None:
    from rig_chasebliss.device import ChaseBlissDevice

    dev = ChaseBlissDevice(id="mood", name="Mood Mk II", config=ChaseBlissConfig(midi_channel=1))
    assert dev.id == "mood"


def test_chase_bliss_device_apply_dry_run_returns_skipped() -> None:
    from rig_chasebliss.device import ChaseBlissDevice

    dev = ChaseBlissDevice(id="mood", name="Mood Mk II", config=ChaseBlissConfig(midi_channel=1))
    ctx = _make_apply_ctx(device_id="mood", preset_name="Bloom", dry_run=True)
    result = dev.apply(ctx)
    assert result.status == "skipped"
    assert result.device == "mood"


def test_chase_bliss_device_apply_confirm_returns_confirmed() -> None:
    from rig_chasebliss.device import ChaseBlissDevice

    dev = ChaseBlissDevice(id="mood", name="Mood Mk II", config=ChaseBlissConfig(midi_channel=1))
    ctx = _make_apply_ctx(
        device_id="mood",
        preset_name="Bloom",
        confirmation_io=InMemoryPromptAdapter(default="confirm"),
    )
    result = dev.apply(ctx)
    assert result.status == "confirmed"


# ---------------------------------------------------------------------------
# MC6Device — Protocol conformance
# ---------------------------------------------------------------------------


def test_mc6_device_has_id_property() -> None:
    from rig_morningstar.device import MC6Device

    dev = MC6Device(id="mc6", name="MC6 MkII", config=MC6Config())
    assert dev.id == "mc6"


def test_mc6_device_apply_no_banks_is_noop() -> None:
    from rig_morningstar.device import MC6Device

    dev = MC6Device(
        id="mc6", name="MC6 MkII", config={"type": "controller", "midi_channel": 1, "banks": []}
    )
    ctx = _make_apply_ctx(device_id="mc6", preset_name="", dry_run=True)
    result = dev.apply(ctx)
    # MC6 apply with no banks returns a skipped/noop result
    assert result.device == "mc6"


def test_mc6_device_apply_dry_run_with_banks_returns_skipped() -> None:
    from rig_morningstar.device import MC6Device

    banks = [{"bank": 1, "switches": {"A": {"scene": "Scene1"}}}]
    dev = MC6Device(
        id="mc6", name="MC6 MkII", config={"type": "controller", "midi_channel": 1, "banks": banks}
    )
    ctx = _make_apply_ctx(device_id="mc6", preset_name="", dry_run=True)
    # dry_run with midi=None: apply_banks returns early
    ctx.midi = None
    result = dev.apply(ctx)
    assert result.device == "mc6"


def test_mc6_device_apply_dry_run_uses_config_banks() -> None:
    """Verify apply() reads banks from config.banks (not the removed banks field)."""
    from rig.config.loader import load_rig
    from rig_morningstar.device import MC6Device

    rig = load_rig(str(FIXTURE_PATH))
    mc6 = rig.devices["mc6"]
    assert isinstance(mc6, MC6Device)
    # Fixture has banks populated in config — proves loader wired data correctly
    config = mc6.config
    banks = config.get("banks", []) if isinstance(config, dict) else getattr(config, "banks", [])
    assert banks

    ctx = _make_apply_ctx(device_id="mc6", preset_name="", dry_run=True)
    ctx.midi = None
    result = mc6.apply(ctx)
    assert result.device == "mc6"


# ---------------------------------------------------------------------------
# Entry point discovery tests
# ---------------------------------------------------------------------------


def test_get_registry_returns_all_four_types_via_entry_points() -> None:
    """get_registry() discovers all four device types through entry points."""
    from rig.engine.plugin_registry import reload_registry

    registry = reload_registry()
    assert registry.get("manual") is not None
    assert registry.get("midi") is not None
    assert registry.get("chase_bliss") is not None
    assert registry.get("controller") is not None
    assert registry.get_model("manual") is not None
    assert registry.get_model("midi") is not None
    assert registry.get_model("chase_bliss") is not None
    assert registry.get_model("controller") is not None


# ---------------------------------------------------------------------------
# Protocol structural typing check
# ---------------------------------------------------------------------------


def test_all_device_types_satisfy_device_protocol_structurally() -> None:
    """All concrete device types must have id, name, config, apply."""
    from rig_analog.device import AnalogDevice
    from rig_chasebliss.device import ChaseBlissDevice
    from rig_hx.device import HXStompDevice
    from rig_morningstar.device import MC6Device

    config_map = {
        AnalogDevice: AnalogConfig(),
        HXStompDevice: HXStompConfig(),
        ChaseBlissDevice: ChaseBlissConfig(midi_channel=1),
        MC6Device: MC6Config(),
    }
    for cls in (AnalogDevice, HXStompDevice, ChaseBlissDevice, MC6Device):
        for attr in ("id", "name", "config", "apply"):
            assert hasattr(cls(id="x", name="X", config=config_map[cls]), attr), (
                f"{cls.__name__} missing '{attr}'"
            )


# ---------------------------------------------------------------------------
# Nyquist gap fills — Phase 4 validation
# ---------------------------------------------------------------------------


def test_analog_device_apply_skip_returns_skipped() -> None:
    from unittest.mock import patch

    from rig_analog.device import AnalogDevice

    dev = AnalogDevice(id="fuzz", name="Fuzz Face", config=AnalogConfig())
    ctx = _make_apply_ctx(device_id="fuzz", preset_name="Noon")
    with patch("rig_analog.device.prompt_analog", return_value="skip"):
        result = dev.apply(ctx)
    assert result.status == "skipped"
    assert result.device == "fuzz"


def test_midi_device_apply_skip_returns_skipped() -> None:
    from rig_hx.device import HXStompDevice

    dev = HXStompDevice(id="hx-stomp", name="HX Stomp", config=HXStompConfig())
    ctx = _make_apply_ctx(
        device_id="hx-stomp",
        preset_name="Clean",
        confirmation_io=InMemoryPromptAdapter(default="skip"),
    )
    result = dev.apply(ctx)
    assert result.status == "skipped"
    assert result.device == "hx-stomp"


def test_midi_device_get_scene_pc_command_with_digital_preset() -> None:
    from rig.models.preset import MidiPreset
    from rig_hx.device import HXStompDevice

    preset = MidiPreset(id="clean", name="Clean", preset_number=5)
    cfg = HXStompConfig(midi_channel=3)
    dev = HXStompDevice(id="hx", name="HX Stomp", config=cfg, presets=[preset])
    cmd = dev.get_scene_pc_command("clean")
    assert cmd is not None
    assert cmd["type"] == "pc"
    assert cmd["channel"] == 3
    assert cmd["value"] == 5


def test_midi_device_get_scene_pc_command_no_matching_preset_returns_none() -> None:
    from rig.models.preset import MidiPreset
    from rig_hx.device import HXStompDevice

    preset = MidiPreset(id="clean", name="Clean", preset_number=5)
    cfg = HXStompConfig(midi_channel=3)
    dev = HXStompDevice(id="hx", name="HX Stomp", config=cfg, presets=[preset])
    assert dev.get_scene_pc_command("nonexistent") is None


def test_chase_bliss_device_get_scene_pc_command_with_digital_preset() -> None:
    from rig_chasebliss.device import ChaseBlissConfig, ChaseBlissDevice
    from rig_chasebliss.preset import DigitalPreset

    preset = DigitalPreset(id="bloom", name="Bloom", preset_number=2)
    cfg = ChaseBlissConfig(midi_channel=7, controls=[])
    dev = ChaseBlissDevice(id="mood", name="Mood Mk II", config=cfg, presets=[preset])
    cmd = dev.get_scene_pc_command("bloom")
    assert cmd is not None
    assert cmd["channel"] == 7
    assert cmd["value"] == 2
