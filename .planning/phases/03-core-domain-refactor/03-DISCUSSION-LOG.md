# Phase 3: Core Domain Refactor - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-04
**Phase:** 03-core-domain-refactor
**Areas discussed:** Rig continuity, Controller node role, DevicePlugin context shape, Graph edge semantics

---

## Rig Continuity

| Option | Description | Selected |
|--------|-------------|----------|
| Rig gains .graph property | load_rig still returns Rig; Rig.graph returns a DeviceGraph. CLI and tests unchanged. | |
| DeviceGraph replaces Rig | load_rig returns DeviceGraph. Rig is aliased/deprecated. All callers update in Phase 4. | |
| Rig IS the DeviceGraph | Rig gains graph methods directly. No separate DeviceGraph type. | ✓ |

**User's choice:** Rig IS the DeviceGraph

| Follow-up: which methods | Description | Selected |
|---|---|---|
| apply_order() only | Topological sort only. Minimal surface. | ✓ |
| apply_order() + edges + device_at(id) | Full traversal surface for Phase 4 and 5. | |
| You decide | Claude picks what makes Phase 4/5 clean. | |

**User's choice:** apply_order() only — keep it minimal.

| Follow-up: sort semantics | Description | Selected |
|---|---|---|
| Sort by signal chain position (simple) | Simple list sort by position index. | |
| Real topological sort with cycle detection | Treats signal chain as directed edges, runs toposort. | |

**User's choice:** (free text) "it's not quite a simple list — the controller will have devices beneath it, so probably a DFS style apply where every child node of a controller gets applied in the 'signal chain' order of the controller's devices"

**Notes:** apply_order() is a DFS traversal from the Controller root, visiting children in signal chain order at each level. Not a simple sort, not a full cycle-detecting toposort — a tree DFS that respects signal chain ordering within each level.

---

## Controller Node Role

| Option | Description | Selected |
|--------|-------------|----------|
| Controller becomes a Device | Controller gets Device-style fields. Scenes stay on Rig for now. | |
| Controller stays separate, referenced in graph | Controller model unchanged. DFS just puts it last. | |
| Controller is just the MC6 — leave it alone | Don't touch Controller in Phase 3. | |

**User's choice:** (free text) "Controller is a root level device in the rig, and one of its properties is 'scenes'. Scenes leaves the rig level device (I believe rig just becomes the topological definition of devices)"

**Notes:** Rig becomes the topological structure; scenes move to Controller; Controller is a root-level device.

| Follow-up: YAML impact | Description | Selected |
|---|---|---|
| Internal model change only | controller.yaml stays as-is. Pure internal restructure. | |
| YAML layout changes too | controller.yaml becomes a device definition. Config-repo migration required. | ✓ |
| You decide | Pick what keeps Phase 3 scoped. | |

**User's choice:** YAML layout changes — "I am NOT CONCERNED AT ALL with breaking my current companion rig repository"

| Follow-up: Controller model | Description | Selected |
|---|---|---|
| Controller is a separate class alongside Device | Peers in graph. Rig holds list[Device | Controller]. | |
| Controller is a Device subtype | DeviceType gains CONTROLLER. MC6Config joins DeviceConfig union. | ✓ |

**User's choice:** "Controller is a special type of device" — i.e., a Device subtype with `DeviceType.CONTROLLER`.

---

## DevicePlugin Context Shape

| Option | Description | Selected |
|--------|-------------|----------|
| One unified PluginContext | Single dataclass for all three methods. plan/diff ignore MIDI. | |
| Separate contexts per operation | PlanContext, DiffContext, ApplyContext — each gets only what it needs. | |
| Reuse ApplyContext from Phase 2 | Zero new types — plan/diff just ignore MIDI/IO fields. | |

**User's choice:** (free text) "The plugins can define their own context decorators (and in the case of MC6 for example, will define MIDI context that they prompt the user for) that wrap the unified PluginContext"

**Notes:** Unified base `PluginContext`; plugins extend it with their own context types for MIDI or other concerns.

| Follow-up: base PluginContext fields | Description | Selected |
|---|---|---|
| state + rig only | Minimal base. Plugins extend for anything else. | |
| state + rig + dry_run | Adds dry_run flag. Useful for apply plugins without needing an extension just for that. | ✓ |
| You decide | Pick minimal base for clean plan/diff plugins. | |

**User's choice:** state + rig + dry_run

---

## Graph Edge Semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Signal chain connections only | Edges = audio/data flow path. DFS from root gives apply order. | |
| Signal chain + ownership | Two edge types: signal path + controller owns scenes/devices. | |
| You decide | Pick what Phase 5 needs without over-building. | |

**User's choice:** (free text) "signal chain, but also flow of data. a controller will be responsible for sending messages (likely PC to start) to change presets — hence the name 'controller'. Eventually devices will 'register' how they want to be triggered."

**Notes:** Edges are signal chain + data flow (Controller sends PC to children). Future: device trigger registration protocol.

| Follow-up: Phase 3 scope | Description | Selected |
|---|---|---|
| Signal chain only for now | Controller trigger relationship is implicit. Deferred to trigger-registration phase. | ✓ |
| Both edge types now | Model signal + trigger edges. Foundation for registration system. | |

**User's choice:** Signal chain only for now.

---

## Claude's Discretion

None — user made explicit choices in all areas.

## Deferred Ideas

- **Device trigger registration protocol** — Devices eventually register how they want to be triggered by Controller (PC, CC, SysEx, etc.). User mentioned this as a future direction.
- **Ownership/dependency edges** — A second edge type was discussed but deferred; signal chain edges are sufficient for Phase 3.
- **Rig.edges / Rig.device_at()** — Graph traversal helpers beyond apply_order() deferred until needed.
- **CLI scenes wiring** — Full update of cli.py to read scenes from Controller deferred to Phase 4 where possible.
