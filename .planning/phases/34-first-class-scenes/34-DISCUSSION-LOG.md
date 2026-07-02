# Phase 34: First-Class Scenes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-01
**Phase:** 34-First-Class Scenes
**Areas discussed:** Migration strategy, Top-level scene source, MC6Config.scenes fate, Controller-less scene apply

---

## Migration Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Hard cutover — drop controller-embedded scenes | Remove `MC6Config.scenes`, update all fixtures now. Existing rig.yaml files with scenes under `config.scenes` break until migrated. Clean, no legacy code path. | ✓ |
| Dual-read with deprecation warning | Loader reads scenes from top-level first; falls back to controller config with a console warning. | |
| Dual-read silently (no warning) | Load from top-level or controller config transparently, indefinitely. | |

**User's choice:** Hard cutover — drop controller-embedded scenes
**Notes:** No compat shim. All fixtures migrate in this phase.

---

## Top-Level Scene Source

| Option | Description | Selected |
|--------|-------------|----------|
| Inline in rig.yaml under `scenes:` | Top-level `scenes:` block in `rig.yaml`. Simple, no directory traversal. | ✓ |
| Separate files — `scenes/<name>.yaml` | Each scene is its own file in a `scenes/` directory. | |
| Both — inline or directory, auto-detect | Loader reads from top-level `scenes:` or `scenes/*.yaml` directory. | |

**User's choice:** Inline in rig.yaml under `scenes:`
**Notes:** Single-file schema only. Directory support is a future concern if rigs get large.

---

## MC6Config.scenes Fate

| Option | Description | Selected |
|--------|-------------|----------|
| Remove it entirely — banks only | MC6Config keeps only `banks`. Scene definitions live at the top level. | ✓ |
| Keep but ignore at load time | Leave field, `extra='ignore'` silently discards it. | |
| Parse but raise a validation error | Loader raises ValidationError if `MC6Config.scenes` is present and non-empty. | |

**User's choice:** Remove it entirely — banks only
**Notes:** Clean break. MC6Config = banks only. Aligns with the hard-cutover decision.

---

## Controller-Less Scene Apply

| Option | Description | Selected |
|--------|-------------|----------|
| Apply device presets, skip MC6 routing | Apply engine sends each device its preset; skips MC6 bank/switch programming if no controller. Controller-free apply works. | ✓ |
| Error — require a controller to apply scenes | `rig apply --scene` errors if no controller device exists. | |
| Warn and partial-apply | Apply device presets and print a warning that no controller was found. | |

**User's choice:** Apply device presets, skip MC6 routing
**Notes:** Scenes as a concept are decoupled from MC6 — they're just preset groups. The controller programs buttons, but the scene itself is device-preset coordination.

---

## Claude's Discretion

- Exact top-level YAML key name (expected to be `scenes:`)
- Whether `Rig.scenes` ordering matters (dict vs ordered dict)
- Whether `MC6Config.extra="ignore"` should be tightened given hard-cutover intent

## Deferred Ideas

None — discussion stayed within phase scope.
