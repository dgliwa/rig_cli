---
plan: "21-01"
phase: 21
status: verified
verified_at: "2026-06-16"
verified_by: "Phase 24 execution (post-MC6 typing fix in Phase 24)"
---

# Phase 21 Verification

## Phase Goal

Each plugin device class carries a concrete config type (not `config: Any`) and a typed preset
list (not `list[Any]`). A `Preset` Protocol exists in `rig.engine.plugin`. The engine sees
`list[Preset]` (or a typed concrete subtype) from all plugins.

## Success Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Each plugin declares a concrete config type — no `config: Any` in plugin source | PASS | grep returns zero hits |
| 2 | `Preset` Protocol exists in `rig.engine.plugin` | PASS | `class Preset(Protocol):` at plugin.py:115 |
| 3 | All plugin device classes declare `presets: list[Preset]` (or typed concrete) — no `list[Any]` | PASS | grep returns zero hits; MC6Device uses `SkipValidation[list[Preset]]` (Phase 24 fix) |
| 4 | `make test` passes with no regressions (309 tests) | PASS | 309 passed |

## Evidence

### Criterion 1 — No `config: Any` in plugin source

Command:
```
grep -rn "config: Any" packages/rig-analog/src/ packages/rig-hx/src/ packages/rig-chasebliss/src/ packages/rig-morningstar/src/
```

Result: **(zero hits)**

Actual config annotations found:
```
packages/rig-analog/src/rig_analog/device.py:32:    config: AnalogConfig
packages/rig-hx/src/rig_hx/device.py:41:    config: HXStompConfig
packages/rig-chasebliss/src/rig_chasebliss/device.py:185:    config: ChaseBlissConfig
packages/rig-morningstar/src/rig_morningstar/device.py:33:    config: MC6Config
```

### Criterion 2 — `Preset` Protocol in `rig.engine.plugin`

Command:
```
grep -n "class Preset" packages/rig/src/rig/engine/plugin.py
```

Result:
```
115:class Preset(Protocol):
```

### Criterion 3 — No `list[Any]` in plugin presets fields

Command:
```
grep -rn "presets.*list\[Any\]" packages/rig-analog/src/ packages/rig-hx/src/ packages/rig-chasebliss/src/ packages/rig-morningstar/src/
```

Result: **(zero hits)**

Actual presets annotations found:
```
packages/rig-analog/src/rig_analog/device.py:34:    presets: list[AnalogPreset] = Field(default_factory=list)
packages/rig-hx/src/rig_hx/device.py:43:    presets: list[HXStompPreset | MidiPreset] = Field(default_factory=list)
packages/rig-chasebliss/src/rig_chasebliss/device.py:187:    presets: list[DigitalPreset] = Field(default_factory=list)
packages/rig-morningstar/src/rig_morningstar/device.py:35:    presets: SkipValidation[list[Preset]] = Field(default_factory=list)
```

**Note on MC6Device:** MC6 never carries real presets (the list is always empty at runtime). Pydantic
cannot validate `list[Protocol]` at field construction time because `Preset` is a non-`runtime_checkable`
Protocol. `SkipValidation[list[Preset]]` preserves the typed annotation for static analysis while
bypassing Pydantic's runtime isinstance check. This satisfies TYPE-03: the annotation is `list[Preset]`,
not `list[Any]`.

### Criterion 4 — Test suite

Command:
```
uv run pytest packages/ -q
```

Result:
```
309 passed in 0.43s
```

## Requirements Satisfied

- **TYPE-02**: All 4 plugin device classes carry concrete config types — no `config: Any` anywhere
- **TYPE-03**: `Preset` Protocol in `rig.engine.plugin`; all plugins declare typed `presets` fields

## Test Delta

- Phase 21 baseline: 309 passing tests (after Phase 20 cleanup)
- After Phase 24 fixes: 309 passing tests
- No regressions introduced
