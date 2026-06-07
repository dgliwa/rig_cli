# Milestones

## v1.1 Package Extraction & Plugin Isolation (Shipped: 2026-06-07)

**Phases completed:** 2 phases, 5 plans

**Key accomplishments:**

1. `rig` discovers devices at runtime via `importlib.metadata.entry_points('rig.devices')` — zero hard imports of any plugin package
2. All 4 plugin packages (`rig-analog`, `rig-chasebliss`, `rig-morningstar`, `rig-hx`) register independently via entry points and are independently installable
3. MIDI connection management moved from engine to device level — each device plugin handles its own MIDI lifecycle in `setup()`
4. `rig.engine.devices.py` deleted — all device classes live in their respective plugin packages
5. HXStompDevice and full ChaseBlissDevice created with per-device MIDI setup, replacing old core device classes
6. Engine MIDI connection loop (Phase -1) removed — `apply_plan()` no longer orchestrates MIDI ports

**Deferred:** CI pipelines, PyPI publishing, plugin authoring guide

---

## v1.0 I/O Decoupling & Plugin Architecture (Shipped: 2026-06-07)

**Phases completed:** 5 phases, 17 plans, 11 tasks

**Key accomplishments:**

- Consolidate CBA state mutations through `mark_preset_saved` and promote `_detect_cba_setup` to a public API to eliminate cross-module private symbol references.
- 1. [Rule 1 - Bug] Plan verify step used invalid single-char side_effect values
- 1. [Rule 3 - Blocking] Global editable install shadows worktree source during pytest
- 1. [Rule 1 - Bug] Updated all affected test _make_rig() helpers and loader.py
- Device Protocol with id/name/config properties replaces DevicePlugin; DeviceApplyContext dataclass added for apply-time context; PluginRegistry gains model-class registration for P3 loader dispatch.
- Four concrete Device Protocol types (AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device) as Pydantic models migrating applier logic into apply() methods, registered in a module-level default PluginRegistry.
- Plugin migration complete: loader.py dispatches via registry, apply.py routes through device.apply(DeviceApplyContext), old applier files deleted — adding a new device type now requires only plugin registration.
- 1. [Rule 1 - Bug] Cold-start warning printed before JSON mode check
- T9 — apply_plan() signature change
- Made `detect_cba_setup()` forward-looking so a single `rig apply` converges a fresh CBA device through all 3 phases, and removed the `_enqueue_new_actions` re-detection from `ChaseBlissApplier`.

---
