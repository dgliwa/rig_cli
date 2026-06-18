---
phase: 27-editor-protocol-cli-yaml-writer
plan: "01"
subsystem: editor-protocol
tags: [protocol, yaml, cli, tdd]
dependency_graph:
  requires: []
  provides:
    - EditorProtocol and EditContext in rig.engine.plugin
    - write_preset() in rig.config.yaml_writer
    - rig edit CLI command
    - skeleton edit() stubs on ChaseBlissDevice and HXStompDevice
  affects:
    - packages/rig/src/rig/engine/plugin.py
    - packages/rig/src/rig/config/yaml_writer.py
    - packages/rig/src/rig/cli/commands/edit.py
    - packages/rig/src/rig/cli/__init__.py
    - packages/rig-chasebliss/src/rig_chasebliss/device.py
    - packages/rig-hx/src/rig_hx/device.py
tech_stack:
  added:
    - ruamel.yaml>=0.18 (round-trip YAML write-back preserving comments)
  patterns:
    - runtime_checkable Protocol for EditorProtocol isinstance dispatch
    - dataclass EditContext mirroring DeviceApplyContext pattern
    - TYPE_CHECKING guard for EditContext import in plugin packages
key_files:
  created:
    - packages/rig/src/rig/config/yaml_writer.py
    - packages/rig/src/rig/cli/commands/edit.py
    - packages/rig/tests/test_yaml_writer.py
    - packages/rig/tests/test_cli_edit.py
  modified:
    - packages/rig/src/rig/engine/plugin.py (EditorProtocol + EditContext added)
    - packages/rig/src/rig/cli/__init__.py (edit registered)
    - packages/rig/pyproject.toml (ruamel.yaml added)
    - packages/rig-chasebliss/src/rig_chasebliss/device.py (edit() skeleton)
    - packages/rig-hx/src/rig_hx/device.py (edit() skeleton)
    - packages/rig/tests/test_plugin.py (EditorProtocol/EditContext tests)
    - packages/rig-chasebliss/tests/test_device.py (edit() tests)
    - packages/rig-hx/tests/test_hx_device.py (edit() tests)
    - packages/rig-analog/tests/test_analog_device.py (negative isinstance test)
decisions:
  - "EditContext fields ordered: config_path, dry_run, confirmation_io, rig — mirrors DeviceApplyContext ordering convention"
  - "write_preset() raises ValueError (not ConfigError) for unknown device/preset to keep yaml_writer free of core error types"
  - "dry_run check in test_edit_dry_run_passes_dry_run_true uses flexible assertion since write_preset() receives dry_run as keyword arg"
metrics:
  duration: "7m 0s"
  completed: "2026-06-17"
  tasks_completed: 4
  files_created: 4
  files_modified: 9
---

# Phase 27 Plan 01: EditorProtocol + YAML Writer + CLI Edit Summary

**One-liner:** EditorProtocol and EditContext protocol contract with ruamel.yaml round-trip write-back and `rig edit` CLI command dispatched via isinstance check on skeleton-stubbed CBA and HX Stomp devices.

## What Was Built

Phase 27 established the full editor lifecycle infrastructure:

1. **EditorProtocol + EditContext** (`plugin.py`) — `@runtime_checkable` companion Protocol with single `edit(preset_id, ctx) -> dict` method. `EditContext` dataclass with `config_path`, `dry_run`, `confirmation_io`, `rig` fields. Device Protocol left structurally identical to before.

2. **yaml_writer.py** — `write_preset()` using `ruamel.yaml` round-trip mode (`YAML(typ='rt')`). Preserves hand-authored YAML comments and field ordering. Raises `ValueError` for unknown device/preset IDs. `dry_run=True` prints a dim "Would write" message and skips the file write entirely.

3. **rig edit CLI command** — Follows the `apply.py` pattern. Routes via `isinstance(device, EditorProtocol)` — no registry, no try/except. Unknown device/preset exit 1 with red error. Non-editor device prints `"Device '{id}' does not support editing."` and exits 0. Save/discard prompt via `ConfirmationIO.prompt()`. `write_preset()` called only on "y"/"yes" response.

4. **Skeleton edit() stubs** — `ChaseBlissDevice.edit()` and `HXStompDevice.edit()` both print the skeleton message and return `preset.model_dump()`. Both satisfy `isinstance(device, EditorProtocol)`. `AnalogDevice` is unchanged and does NOT implement `EditorProtocol`.

## Task Commits

| Task | Type | Hash | Description |
|------|------|------|-------------|
| 1 RED | test | 9be9a31 | test(plugin): add EditorProtocol/EditContext tests |
| 1 GREEN | feat | f2c04ce | feat(plugin): add EditorProtocol and EditContext |
| 2 RED | test | 13370e0 | test(yaml-writer): add write_preset round-trip tests |
| 2 GREEN | feat | 0aef05f | feat(yaml-writer): add write_preset with ruamel.yaml round-trip |
| 3 RED | test | 4d590fc | test(cli/edit): add edit command routing tests |
| 3 GREEN | feat | 8b7eb9e | feat(cli/edit): add rig edit command |
| 4 RED | test | 71ccbb6 | test(cba): add skeleton edit() stub tests for CBA, HX, and Analog devices |
| 4 GREEN | feat | 21c40e3 | feat(cba): add skeleton edit() stub on ChaseBlissDevice and HXStompDevice |

## Verification Results

- `uv run pytest packages/ -q`: **359 passed, 0 failed**
- `uv run rig --help | grep edit`: `edit` command appears with correct description
- `uv run rig edit --help`: Shows `device_id`, `preset_id` positional args and `--dry-run` option
- `isinstance(ChaseBlissDevice(...), EditorProtocol)`: True
- `isinstance(HXStompDevice(...), EditorProtocol)`: True
- `isinstance(AnalogDevice(...), EditorProtocol)`: False
- `ruamel.yaml>=0.18` in packages/rig/pyproject.toml: confirmed
- yaml_writer round-trip comment preservation test: passes

## Deviations from Plan

None — plan executed exactly as written with one minor auto-adjustment:

**Test fix (not a deviation):** `test_edit_dry_run_passes_dry_run_true` initially asserted `call_args[0][4] is True` but the implementation passes `dry_run` as a keyword argument. Updated the assertion to check both positional and keyword args — functionally equivalent, behavior correct.

## Known Stubs

The `edit()` methods on ChaseBlissDevice and HXStompDevice print `"no interactive editing available — Phase 28 will add this"` and return current preset field values. These are **intentional skeleton stubs** per D-07/D-08, not blocking stubs — the plan's goal of establishing the protocol and CLI surface is fully achieved. Phase 28 will replace these with interactive editing flows.

## Threat Surface Scan

No new threat surface beyond what the plan's threat model covers. The `write_preset()` write is gated behind explicit user confirmation (T-27-01 mitigated). Device/preset IDs validated before dispatch (T-27-02 mitigated). No new network endpoints, auth paths, or schema changes introduced.

## Self-Check: PASSED

Files exist:
- packages/rig/src/rig/engine/plugin.py — FOUND
- packages/rig/src/rig/config/yaml_writer.py — FOUND
- packages/rig/src/rig/cli/commands/edit.py — FOUND
- packages/rig/tests/test_yaml_writer.py — FOUND
- packages/rig/tests/test_cli_edit.py — FOUND

Commits exist: 9be9a31, f2c04ce, 13370e0, 0aef05f, 4d590fc, 8b7eb9e, 71ccbb6, 21c40e3 — all confirmed in git log.
