# Requirements: rig-cli

**Defined:** 2026-06-17
**Core Value:** A single command should bring the physical rig to the exact state described in the config repo — no guessing, no manual knob-hunting.

## v1.5 Requirements

### I/O Parity

- [x] **IO-01**: User's analog device prompts route through `ConfirmationIO.prompt()` — no `builtins.input` call in `AnalogApplier`
- [x] **IO-02**: AnalogApplier tests use `InMemoryPromptAdapter` — no `builtins.input` monkeypatching

### Isolated Preset Apply

- [x] **PRESET-01**: User can run `rig apply --device <id> --preset <id>` to apply one device's preset without triggering full scene setup
- [x] **PRESET-02**: When `--device` and `--preset` flags are given, apply skips all other devices
- [x] **PRESET-03**: `rig apply --device <id> --preset <id>` updates `state.json` for the targeted device only

### Editor Mode

- [x] **EDIT-01**: Device Protocol gains an `edit(preset_id, ctx)` method (or companion Protocol) — each plugin owns its interactive editing behavior
- [x] **EDIT-02**: User can run `rig edit <device-id> <preset-id>` to enter editor mode for a device's preset
- [x] **EDIT-03**: During editor mode, CC-based plugins send live CC values to the device as values are changed interactively
- [x] **EDIT-04**: When the user saves, editor mode writes updated preset values back to `rig.yaml`
- [x] **EDIT-05**: When the user discards, `rig.yaml` is unchanged
- [x] **EDIT-06**: Analog plugin editor mode presents a prompt-per-control flow (no live MIDI — manual set); plugin owns this behavior

## Future Requirements

### Structured Preset Subcommand

- **PKG-01**: `rig preset apply <device> <preset>` subcommand group (after --flag approach ships)
- **PKG-02**: `rig preset list <device>` — show all known presets for a device with their state

## Out of Scope

| Feature | Reason |
|---------|--------|
| `rig edit` for controllers (MC6) | MC6 editing is a different domain (bank/switch config, not CC values) — defer |
| Live CC preview without confirming | Out-of-scope for v1.5; editor mode saves or discards atomically |
| Full HX SysEx read/write (#3) | Requires MIDI SysEx parsing complexity — future milestone |
| Complex MC6 workflows (#6) | Low-priority — defer |
| UI (#18) | Speculative — not planned |
| MC6 clear message emulation (#17) | Deferred bug fix |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| IO-01 | Phase 25 | Complete |
| IO-02 | Phase 25 | Complete |
| PRESET-01 | Phase 26 | Complete |
| PRESET-02 | Phase 26 | Complete |
| PRESET-03 | Phase 26 | Complete |
| EDIT-01 | Phase 27 | Complete |
| EDIT-02 | Phase 27 | Complete |
| EDIT-04 | Phase 27 | Complete |
| EDIT-05 | Phase 27 | Complete |
| EDIT-03 | Phase 28 | Complete |
| EDIT-06 | Phase 28 | Complete |

**Coverage:**

- v1.5 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-17*
*Last updated: 2026-06-17 — v1.5 requirements all complete; checkboxes and traceability updated*
