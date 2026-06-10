---
title: Remove controls from ChaseBlissConfig
quick_id: 260610-vae
slug: remove-controls-from-chaseblissconfig
status: pending
created: 2026-06-10
files_modified:
  - packages/rig-chasebliss/src/rig_chasebliss/device.py
  - packages/rig-chasebliss/src/rig_chasebliss/applier.py
  - packages/rig-chasebliss/tests/test_device.py
  - packages/rig/tests/fixtures/sample_rig/rig.yaml
---

## Goal

`ChaseBlissConfig.controls` is a redundant field — controls are always sourced from the catalog
keyed by `(brand, model)`. Remove the field and the `get_cc_params` instance method from the
config model; resolve controls at call sites from the catalog instead. This eliminates the
possibility of stale/overridden controls in YAML and removes the catalog-fallback patching
workaround in `from_raw_yaml`.

---

## Tasks

### 1. Strip `controls` and `get_cc_params` from `ChaseBlissConfig` in `device.py`

File: `packages/rig-chasebliss/src/rig_chasebliss/device.py`

- Remove the `controls: list[Control] = []` field from `ChaseBlissConfig`.
- Remove the `get_cc_params(self, parameters)` instance method from `ChaseBlissConfig`.
- Add a module-level standalone helper `_get_cc_params(parameters: dict[str, Any], controls: list[Control]) -> list[dict[str, int]]` that contains the same logic (iterate controls, check `midi_cc is not None` and `name in parameters`, return `[{"cc": ctrl.midi_cc, "value": int(parameters[ctrl.name])}]`).
- In `_detect_cba_setup_for_device`, resolve controls at the top of the function body:
  ```
  controls = get_controls("Chase Bliss Audio", device.config.model) or []
  ```
  Then pass `controls` to `validate_cc_params(preset.parameters, controls)` (already the signature) and replace `device.config.get_cc_params(preset.parameters)` with `_get_cc_params(preset.parameters, controls)`.
- In `ChaseBlissDevice.from_raw_yaml`, remove the entire `if not config.controls and config.model:` block that patches `config.controls` from the catalog — it is no longer needed.
- `get_controls` is already imported at the top of `device.py`; no import changes required.

Verify: `uv run pytest packages/rig-chasebliss/tests/ -q` passes (some tests will fail until Task 2 fixes them — run full suite after Task 2).

---

### 2. Update `applier.py` — replace `device.config.controls` with catalog lookup

File: `packages/rig-chasebliss/src/rig_chasebliss/applier.py`

There are two references to `device.config.controls` inside `_build_preset`:

**Dry-run branch (lines ~144–151):** The `hasattr(device.config, "controls")` guard and the list comprehension that counts `reset_count` both use `device.config.controls`. Replace with:
```python
from rig_chasebliss.catalog import get_controls
controls = get_controls("Chase Bliss Audio", getattr(device.config, "model", None) or "") or []
reset_count = len([c for c in controls if c.default is not None and c.midi_cc is not None])
```
Remove the `hasattr` guard — `controls` will always be a list (empty if model unknown).

**`_send_reset_ccs` inner function (lines ~174–177):** Replace the `hasattr(device.config, "controls")` guard and `device.config.controls` reference with:
```python
from rig_chasebliss.catalog import get_controls
controls = get_controls("Chase Bliss Audio", getattr(device.config, "model", None) or "") or []
resettable = [c for c in controls if c.default is not None and c.midi_cc is not None]
```

Move the `get_controls` import to the top of `applier.py` (alongside existing imports from `rig_chasebliss`) rather than inlining it in two places.

Verify: `uv run pytest packages/rig-chasebliss/tests/ -q` passes (after Task 3 test updates).

---

### 3. Update `test_device.py` and `rig.yaml` fixture

File: `packages/rig-chasebliss/tests/test_device.py`

Remove or replace the three tests that assert on `device.config.controls`:

- `test_from_raw_yaml_known_model_populates_controls` — remove it. The catalog lookup now happens at call sites, not on the config object. Replace with a test that confirms `_detect_cba_setup_for_device` (or `validate_cc_params` called with catalog controls) works for a known model: build a minimal `ChaseBlissDevice` with `model="Mood MkII"`, call `get_controls("Chase Bliss Audio", "Mood MkII")`, assert the result is non-empty and contains a control named `"time"`.

- `test_from_raw_yaml_unknown_model_leaves_controls_empty` — remove it. `ChaseBlissConfig` no longer has `controls`. Replace with a simpler smoke test: `ChaseBlissDevice.from_raw_yaml({"id": "x", "config": {"type": "chase_bliss", "model": "Nonexistent"}})` should construct without error and `device.config.model == "Nonexistent"`.

- `test_from_raw_yaml_explicit_controls_not_overwritten` — remove it entirely. This behavior no longer exists: `ChaseBlissConfig` does not accept `controls` from YAML.

No changes needed to the `validate_cc_params` tests (lines 1–109) — they pass `controls` explicitly and are unaffected.

File: `packages/rig/tests/fixtures/sample_rig/rig.yaml`

Remove the `controls:` block from the `mood` device config (lines 10–135 of current file). The `mood` device should retain `type: chase_bliss` and `midi_channel: 2` only. The `model` key must be present for catalog resolution to work — add `model: "Mood MkII"` to the mood device config so that `_detect_cba_setup_for_device` can resolve controls at runtime.

The fixture `presets` block for `mood` (preset-1 "Shimmer Delay") uses parameter names like `micro_looper_modify`. Verify against the catalog — `catalog.py` has `loop_modify` (CC 19), not `micro_looper_modify`. Update the preset parameters in the fixture to use the catalog-correct name `loop_modify` if the existing name is wrong, so integration tests that load this fixture won't fail validation.

Similarly, `micro_bypass` and `wet_bypass` — confirm names against `MOOD_MKII_CONTROLS` in `catalog.py` and correct if needed.

Verify: `uv run pytest packages/ -q` — full suite green.

---

## must_haves

- [ ] `ChaseBlissConfig` has no `controls` field and no `get_cc_params` method
- [ ] `ChaseBlissConfig` constructed from YAML silently ignores any `controls:` key (Pydantic default behavior — extra fields ignored or raises, confirm model config handles gracefully)
- [ ] `_get_cc_params` standalone helper exists in `device.py` and is used by `_detect_cba_setup_for_device`
- [ ] `_detect_cba_setup_for_device` calls `get_controls("Chase Bliss Audio", device.config.model)` to resolve controls
- [ ] `applier.py` has no references to `device.config.controls` or `hasattr(device.config, "controls")`
- [ ] `rig.yaml` fixture has no `controls:` block; mood device has `model: "Mood MkII"`
- [ ] All three removed `test_from_raw_yaml_*_controls` tests are replaced with equivalent coverage that does not assert on `config.controls`
- [ ] `uv run pytest packages/ -q` passes with no failures
