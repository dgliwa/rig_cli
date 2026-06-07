---
phase: 4
plan: P4
type: gap-closure
wave: 4
depends_on: [P1, P2, P3]
files_modified:
  - src/rig/engine/devices.py
  - tests/test_devices.py
autonomous: true
requirements: []
must_haves:
  - MC6Device.apply() reads banks from self.config.banks, not self.banks
  - self.banks field removed from MC6Device (unused, misleading)
  - Existing tests updated to construct config with banks rather than pass banks kwarg
  - New test verifies banks path is exercised when loaded from sample_rig fixture
---

# Phase 4 Gap Closure: MC6Device.apply() Banks Disconnect

## Context

Verification score: 11/12. One partial failure identified:

> `MC6Device.apply()` uses `self.banks` (always `[]`) instead of `self.config.banks`.
> The loader populates banks via `ControllerConfig.banks`; `MC6Device.banks` is never written.
> In production, MC6 programming silently returns `"skipped"` instead of executing.

**Root cause:** `MC6Device` declares `banks: list[dict] = []` as a Pydantic field. The loader constructs MC6Device via `_parse_device`, which passes `config=ControllerConfig(banks=[...])`. The `banks` field on `MC6Device` itself is never populated by the loader — only `config.banks` is.

## Task P4-T1: Fix MC6Device.apply() to read self.config.banks

**File:** `src/rig/engine/devices.py`

**Changes:**

1. **Remove** `banks: list[dict] = []` field from `MC6Device` (line 278).
   It is never populated by the loader and misleads readers into thinking it's the source of truth.

2. **Line 301** — change early-exit guard:
   ```python
   # Before
   if not self.banks or ctx.midi is None:
   # After
   if not getattr(self.config, "banks", None) or ctx.midi is None:
   ```

3. **Line 307** — change dry-run iteration:
   ```python
   # Before
   for bank in self.banks:
   # After
   for bank in self.config.banks:
   ```

4. **Line 327** — change live-apply iteration:
   ```python
   # Before
   for bank in self.banks:
   # After
   for bank in self.config.banks:
   ```

Use `getattr(self.config, "banks", None)` for the guard (line 301) to safely handle cases where `config` is `None` (prototype registry instances). For lines 307 and 327, `self.config.banks` is safe because those branches are only reached when the guard passed.

## Task P4-T2: Update existing tests

**File:** `tests/test_devices.py`

Two tests currently pass `banks=...` directly to `MC6Device`:

### test_mc6_device_apply_no_banks_returns_skipped (line ~309)

Old:
```python
dev = MC6Device(id="mc6", name="MC6 MkII", config=object(), banks=[])
```
New — use a `ControllerConfig` with empty banks:
```python
from rig.models.device import ControllerConfig
dev = MC6Device(id="mc6", name="MC6 MkII", config=ControllerConfig(midi_channel=1, banks=[]))
```

### test_mc6_device_apply_dry_run_with_banks_returns_skipped (line ~317)

Old:
```python
banks = [{"bank": 1, "switches": {"A": {"scene": "Scene1"}}}]
dev = MC6Device(id="mc6", name="MC6 MkII", config=object(), banks=banks)
```
New:
```python
from rig.models.device import ControllerConfig
banks = [{"bank": 1, "switches": {"A": {"scene": "Scene1"}}}]
dev = MC6Device(id="mc6", name="MC6 MkII", config=ControllerConfig(midi_channel=1, banks=banks))
```

The test assertions stay identical — only the construction changes.

## Task P4-T3: Add banks path coverage test using sample_rig fixture

**File:** `tests/test_devices.py`

Add a new test after the existing MC6Device tests that:

1. Loads the sample_rig fixture via `load_rig` (the fixture at `tests/fixtures/sample_rig/` has `devices/mc6.yaml` with `config.banks` populated)
2. Retrieves the MC6Device from `rig.devices["mc6"]`
3. Constructs a minimal `DeviceApplyContext` with `dry_run=True`, `midi=None` (to avoid MIDI hardware calls), and a dummy action
4. Asserts that `apply()` reaches the dry-run banks loop (not early-exit) — confirmed by checking the return status is `"skipped"` (dry-run returns skipped after printing, not before) OR by asserting the config.banks is non-empty before calling apply

The key assertion: `mc6.config.banks` is non-empty AND `apply()` returns a result with `device == "mc6"` — proving the code path entered the dry-run loop rather than the early guard exit.

```python
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_rig"

def test_mc6_device_apply_dry_run_uses_config_banks() -> None:
    """Verify apply() reads banks from config.banks (not the removed banks field)."""
    from rig.config.loader import load_rig
    from rig.engine.devices import MC6Device

    rig = load_rig(str(FIXTURE_PATH))
    mc6 = rig.devices["mc6"]
    assert isinstance(mc6, MC6Device)
    # Fixture has banks populated in config — proves loader wired data correctly
    assert mc6.config.banks

    ctx = _make_apply_ctx(device_id="mc6", preset_name="", dry_run=True)
    ctx.midi = None
    result = mc6.apply(ctx)
    assert result.device == "mc6"
```

Use an inline `load_rig` call against the sample_rig fixture directory (the established pattern in `test_loader.py`). No pytest fixture parameter needed.

## Verification

After all tasks complete:

- [ ] `make test` passes (238+ tests)
- [ ] `MC6Device` no longer has a `banks` field — grep confirms `self.banks` absent from `devices.py`
- [ ] `mc6.config.banks` is used in all three locations in `apply()`
- [ ] New test exercises the config.banks path on a real fixture-loaded MC6Device
