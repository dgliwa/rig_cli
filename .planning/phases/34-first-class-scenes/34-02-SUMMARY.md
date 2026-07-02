---
id: "34-02"
phase: 34
plan: 02
status: complete
completed: "2026-07-02"
---

# Summary: Controller-less apply coverage + cleanup (34-02)

## What was built

- **Controller-less apply test (D-05):** `TestControllerlessApply.test_apply_scene_without_controller_device_skips_controller_phase` — builds a Rig with scenes and only non-controller devices (no CONTROLLER device), runs `compute_plan` + `apply_plan`, and asserts: (a) apply completes without cancellation, (b) device state is written for the targeted device, (c) the scene is recorded in `state.scenes`, and (d) controller programming (Phase 2) is skipped because `rig.controller is None`.
- **Stale guard removed:** `MC6Device.apply()` no longer uses `hasattr(rig, "scenes")` — simplified to `rig.scenes.get(scene_name) if rig else None` since `Rig.scenes` is always a real field after 34-01.
- **Lint fix:** Pre-existing import-order issue in `test_yaml_writer.py` fixed (ruff I001).

## Must-haves achieved

1. `apply_plan` applies scene device presets when rig has scenes but no CONTROLLER device; skips MC6 programming phase — **proven by passing test** (D-05).
2. `MC6Device.apply()` `hasattr(rig, "scenes")` guard removed — `rig.scenes.get(...)` used directly.
3. Loader docstring reflects top-level `scenes:` schema (confirmed correct from 34-01, no changes needed).
4. `make test` passes — **407 tests green**.
5. `make lint` passes clean.

## Commits

- `8ce1ba4` — `test(34-02): add controller-less apply coverage for D-05`
- `56d2d83` — `refactor(34-02): remove stale hasattr guard from MC6Device.apply()`
