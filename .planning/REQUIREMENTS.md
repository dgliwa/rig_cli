# Requirements — v1.2 Cleaner Core

## Overview

Collapse the multi-file config repo into a single flat `rig.yaml`, strip all plugin-specific code from core, and remove backwards-compat shims introduced in v1.0/v1.1. No backwards compatibility — clean break.

---

## Active Requirements

### SCHEMA — Single-file rig.yaml

- [ ] **SCHEMA-01**: User can define the entire rig in a single `rig.yaml` file (no multi-file layout required)
- [ ] **SCHEMA-02**: Device list order in `rig.yaml` defines the signal chain — no separate signal chain config needed
- [ ] **SCHEMA-03**: `SignalChainPosition` model is removed from core
- [ ] **SCHEMA-04**: A controller device (e.g. `type: mc6`) optionally references the device IDs it composes
- [ ] **SCHEMA-05**: Scenes are defined inside the controller device with `bank`, `switch`, and `presets: {device_id: preset_id}` mapping
- [ ] **SCHEMA-06**: Device identity is expressed via `type` only — `manufacturer`/`model` removed from core `Device`

### MODEL — Core model cleanup

- [ ] **MODEL-01**: `ManualConfig`, `MidiConfig`, `ChaseBlissConfig`, `ControllerConfig` removed from core; live only in plugins
- [ ] **MODEL-02**: `Control` and `ControlType` removed from core
- [ ] **MODEL-03**: `Rig` model drops all compat shims: `pedals`, `digital_presets`, `hx_presets`, `analog_presets`, `mc6`, `_controller_device`
- [ ] **MODEL-04**: `Scene` model drops `mc6_bank` and `mc6_switch` fields

### LOADER — Single-file parser

- [ ] **LOADER-01**: `load_rig()` parses a single `rig.yaml` instead of the multi-file directory layout
- [ ] **LOADER-02**: Device construction dispatched to plugins via entry points using the `type` field as the lookup key

### CLEANUP — Dead code & compat removal

- [ ] **CLEANUP-01**: All `TODO: 1.2` markers and their associated dead code removed from the codebase
- [ ] **CLEANUP-02**: Multi-file config repo support removed — only single `rig.yaml` is accepted

---

## Future Requirements

- Plugin authoring documentation (deferred from v1.1)
- Signal chain visualization / ordering UI
- Multi-controller rig support (multiple MC6s or mixing controller types)

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Plugin internal implementations | Plugin packages own their own code; this milestone touches only core |
| CLI command surface changes | Only changes forced by schema/model changes are included |
| New user-facing features | This is a refactor milestone — no new capabilities |
| Backwards compatibility shims | Explicitly excluded; clean break is a milestone goal |

---

## Traceability

| REQ-ID | Phase | Plan |
|--------|-------|------|
| SCHEMA-01 | — | — |
| SCHEMA-02 | — | — |
| SCHEMA-03 | — | — |
| SCHEMA-04 | — | — |
| SCHEMA-05 | — | — |
| SCHEMA-06 | — | — |
| MODEL-01 | — | — |
| MODEL-02 | — | — |
| MODEL-03 | — | — |
| MODEL-04 | — | — |
| LOADER-01 | — | — |
| LOADER-02 | — | — |
| CLEANUP-01 | — | — |
| CLEANUP-02 | — | — |
