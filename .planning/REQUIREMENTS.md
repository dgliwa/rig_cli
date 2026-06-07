# Requirements: rig-cli

**Defined:** 2026-06-07
**Core Value:** A single command should bring the physical rig to the exact state described in the config repo — no guessing, no manual knob-hunting.

## v1.1 Requirements

### Core

- [ ] **CORE-01**: `rig` publishes `rig.devices` entry point group with standard schema
- [ ] **CORE-02**: Plugin discovery via `importlib.metadata.entry_points('rig.devices')` at runtime — no hard imports of any plugin
- [ ] **CORE-03**: Migration from code-internal `PluginRegistry` to entry-point discovery (backward-compatible path)
- [ ] **CORE-04**: `rig` has zero `[project.dependencies]` on any device plugin package

### Device Plugins

- [ ] **ANLG-01**: `rig-analog` is a separate pip package with its own `pyproject.toml`, registers AnalogDevice via entry point
- [ ] **CHASE-01**: `rig-chasebliss` is a separate pip package with its own `pyproject.toml`, registers ChaseBlissDevice via entry point, manages its own MIDI connection for setup phases
- [ ] **MC6-01**: `rig-morningstar` is a separate pip package with its own `pyproject.toml`, registers MC6Device via entry point, manages its own MIDI connection for bank/switch config
- [ ] **HX-01**: `rig-hx` is a separate pip package with its own `pyproject.toml`, registers HXStompDevice via entry point

### Build & Release

- [ ] **BUILD-01**: Each package versioned independently with `pyproject.toml`
- [ ] **BUILD-02**: Editable installs work for local dev (`pip install -e packages/rig-*`)
- [ ] **BUILD-03**: CI publishes each package independently

### Docs

- [ ] **DOCS-01**: Plugin authoring guide — entry point contract, expected interface, example

## v2 Requirements

None currently.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full HX SysEx read/write via MIDI | Requires MIDI SysEx parsing complexity — future milestone |
| HX MIDI channel configurability | Current hardcoded channel works |
| Complex MC6 workflows (next page, MIDI clock, etc.) | Low-priority feature work |
| CBA Mood MkII / Wombtone / Brothers MIDI catalog | Separate device-support work |
| MC6 clear message emulation | Deferred bug fix |
| UI | Speculative — not planned |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | Phase 6 | Pending |
| CORE-02 | Phase 6 | Pending |
| CORE-03 | Phase 6 | Pending |
| CORE-04 | Phase 6 | Pending |
| ANLG-01 | Phase 7 | Pending |
| CHASE-01 | Phase 7 | Pending |
| MC6-01 | Phase 7 | Pending |
| HX-01 | Phase 7 | Pending |
| BUILD-01 | Phase 8 | Pending |
| BUILD-02 | Phase 8 | Pending |
| BUILD-03 | Phase 8 | Pending |
| DOCS-01 | Phase 8 | Pending |

**Coverage:**
- v1.1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-07*
