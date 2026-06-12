# Requirements: rig-cli v1.4

**Defined:** 2026-06-12
**Core Value:** A single command should bring the physical rig to the exact state described in the config repo — no guessing, no manual knob-hunting.

## v1.4 Requirements

Internal refactor milestone — zero user-visible behavior changes. Eliminates the parallel device model systems, establishes a single typed boundary throughout the plugin/core interface, and closes all test and code-quality debt.

### TYPE — Type System & Model Consolidation

- [ ] **TYPE-01**: The codebase has a single `Device` type surface — the legacy `Device(BaseModel)` in `models/device.py` is retired; `Rig.devices` is typed `dict[str, Device]` against the Protocol; all code paths that touch `rig.devices` are type-safe without `Any` or `hasattr` guards
- [ ] **TYPE-02**: Each plugin device class carries a concrete config type (`config: ChaseBlissConfig`, `config: HXStompConfig`, etc.) — not `config: Any`; construction from YAML validates against the concrete type
- [ ] **TYPE-03**: A `Preset` Protocol exists in `rig.engine.plugin`; all plugin device classes declare `presets: list[Preset]`; the engine no longer sees `list[Any]`
- [ ] **TYPE-04**: The dead `plan()` and `diff()` methods are removed from the `Device` Protocol and all plugin implementations (they raise `NotImplementedError` and are never called by the engine)
- [ ] **TYPE-05**: `apply.py` has one `ApplyContext` type (the `DeviceApplyContext` dataclass from `engine.plugin`) — the legacy `ApplyContext` dataclass in `appliers/base.py` is retired or clearly scoped; no function passes both types

### TEST — Test Infrastructure

- [ ] **TEST-01**: The stale root-level `tests/` directory is deleted — it contains broken imports from a pre-plugin-extraction layout and fails collection with 9 import errors; `make test` runs and passes
- [ ] **TEST-02**: The 3 failing tests (`test_build_preset_confirm_…`, `test_midi_connect_and_send`, `test_cba_channel_establishment_…`) pass without `-s` — the interaction functions they exercise route through the `ConfirmationIO` Protocol so test doubles replace `input()` calls

### QUAL — Code Quality

- [ ] **QUAL-01**: All raw string device-type comparisons (`== "analog"`, `== "digital"`, `== "controller"`, `== "modeler"`) in engine and plugin code are replaced with `DeviceType` enum members; a grep for these patterns in non-test source returns zero hits
- [ ] **QUAL-02**: The TODO comment in `models/device.py` about Enums vs Literals is resolved with a recorded decision: `Literal` is used for Pydantic discriminated union `type` fields (required by Pydantic); `DeviceType` StrEnum is used for runtime comparisons; the two are not in conflict

## Future Requirements (v1.5)

Deferred to the next milestone (Terraform Loop Completeness).

### PLAN — Field-Level Plan Diffs

- **PLAN-01**: `rig plan` shows which specific CC values / knob positions changed for a device, not just that a scene is "changed"
- **PLAN-02**: `rig plan` output per device-action includes before/after values for each changed parameter

### APPLY — Idempotency & Targeting

- **APPLY-01**: `rig apply` skips the manual knob prompt for an analog device when `state.json` already records that device in the desired preset
- **APPLY-02**: `rig apply --device <id>` applies only the named device's actions across all scenes — equivalent to `-target` in Terraform

## Out of Scope

| Feature | Reason |
|---------|--------|
| Drift detection | Most MIDI devices cannot report state back; would require user-initiated reset flow — defer indefinitely |
| Rollback / `rig destroy` | No clear semantics for MIDI devices — out of scope |
| Plugin authoring docs (PKG-07) | Deferred from v1.3; remains active but not this milestone's focus |
| Remote state (S3, etc.) | `.rig/state.json` is intentionally local — single-user tool |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TYPE-01 | Phase 22 | Pending |
| TYPE-02 | Phase 21 | Pending |
| TYPE-03 | Phase 21 | Pending |
| TYPE-04 | Phase 20 | Pending |
| TYPE-05 | Phase 23 | Pending |
| TEST-01 | Phase 20 | Pending |
| TEST-02 | Phase 23 | Pending |
| QUAL-01 | Phase 20 | Pending |
| QUAL-02 | Phase 20 | Pending |

**Coverage:**
- v1.4 requirements: 9 total
- Mapped to phases: 9 (complete)
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-12*
*Last updated: 2026-06-12 after roadmap creation*
