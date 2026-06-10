---
quick_id: 260610-vae
status: complete
date: 2026-06-10
commit: 63ddd9d
---

## What changed

Removed `controls: list[Control]` field and `get_cc_params` instance method from `ChaseBlissConfig`. Controls are now resolved at call sites from the catalog via `get_controls("Chase Bliss Audio", model)`. Added `extra="ignore"` to `ChaseBlissConfig` so existing YAML files with a `controls:` block are silently tolerated without error. Introduced a standalone `_get_cc_params(parameters, controls)` module-level function in `device.py`. Updated `_detect_cba_setup_for_device` and both dry-run and reset paths in `applier.py` to resolve controls at runtime. Fixed the sample_rig fixture: removed the inline controls block, added `model: "Mood MkII"`, and corrected two stale parameter names (`micro_looper_modify` → `loop_modify`, `micro_bypass` → `loop_bypass`) to match catalog names.

## Files modified

- `packages/rig-chasebliss/src/rig_chasebliss/device.py` — removed `controls` field and `get_cc_params` from `ChaseBlissConfig`; added `extra="ignore"`; added `_get_cc_params` function; updated `_detect_cba_setup_for_device` and `from_raw_yaml`
- `packages/rig-chasebliss/src/rig_chasebliss/applier.py` — imported `get_controls`; updated `_build_preset` dry-run reset_count logic and `_send_reset_ccs` closure to resolve controls from catalog
- `packages/rig-chasebliss/tests/test_device.py` — updated tests to reflect `ChaseBlissConfig` no longer having `controls`; replaced controls-population assertions with model-name and extra-ignore assertions
- `packages/rig-chasebliss/tests/test_applier.py` — replaced `_make_rig(controls)` pattern with `_make_rig()` + `_patch_get_controls(controls)` context manager; rewrote all reset-behavior tests to patch `get_controls` at the applier call site
- `packages/rig/tests/fixtures/sample_rig/rig.yaml` — removed inline controls block; added `model: "Mood MkII"`; fixed `micro_looper_modify` → `loop_modify` and `micro_bypass` → `loop_bypass`
- `packages/rig/tests/test_catalog.py` — migrated `TestGetCcParams` from `cfg.get_cc_params(...)` to `_get_cc_params(..., controls)` standalone function
