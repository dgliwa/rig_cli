# Phase 24: Close v1.4 gaps: Phase 21 verification, MC6 preset typing, QUAL-01 DeviceAction - Context

**Gathered:** 2026-06-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Three gap-closing items left open from earlier v1.4 phases:

1. **Phase 21 VERIFICATION.md** — write the missing verification document confirming all Phase 21
   success criteria hold in the current codebase (after the MC6 fix below satisfies criterion #3).

2. **MC6 preset typing** — change `MC6Device.presets: list[Any]` to `list[Preset]` so the
   Morningstar plugin conforms to the `Preset` Protocol and Phase 21 criterion #3 is fully met.

3. **DeviceAction enum types** — change `DeviceAction.device_type: str` → `DeviceType` and
   introduce a new `ActionStatus` StrEnum for `DeviceAction.status`, replacing the raw `Literal`
   with enum values. Also update REQUIREMENTS.md to mark TYPE-02 and TYPE-03 as complete.

Zero user-visible behavior changes.

</domain>

<decisions>
## Implementation Decisions

### MC6 preset typing
- **D-01:** Change `MC6Device.presets: list[Any]` → `list[Preset]` with `Field(default_factory=list)`.
  MC6 never carries real presets — the list is always empty — but the Protocol requires `list[Preset]`.
  Direct import: `from rig.engine.plugin import Preset` (MC6Device already imports from there).

### DeviceAction.device_type
- **D-02:** Change `DeviceAction.device_type: str` → `DeviceType`. Pydantic serializes `StrEnum`
  as its `.value` automatically, so JSON output is unchanged.
- **D-03:** Update the two raw-string construction sites:
  - `compute.py:93` — `device_type="analog"` → `device_type=DeviceType.ANALOG`
  - `apply.py:165` — `device_type="controller"` → `device_type=DeviceType.CONTROLLER`
  - `compute.py:118` already uses `device_type=pedal.type.value` — change to `device_type=pedal.type`
    (pass the enum member directly now that the field is typed).

### DeviceAction.status
- **D-04:** Introduce `class ActionStatus(StrEnum)` with `CONFIGURE = "configure"`,
  `VERIFY = "verify"`, `ANALOG = "analog"` — parallel pattern to `DeviceType`.
  Place it in `engine/plan/models.py` alongside `DeviceAction`.
- **D-05:** Change `DeviceAction.status: Literal["configure", "verify", "analog"]` → `ActionStatus`.
  Update all construction sites to use `ActionStatus.CONFIGURE`, `ActionStatus.VERIFY`,
  `ActionStatus.ANALOG`.

### Phase 21 verification and requirements cleanup
- **D-06:** Write Phase 21 VERIFICATION.md **after** the MC6 fix is in place so all 4 criteria pass.
  File location: `.planning/phases/21-concrete-types-plugin-boundary/21-01-VERIFICATION.md`.
- **D-07:** Update REQUIREMENTS.md — mark TYPE-02 and TYPE-03 as `[x]` complete (they were
  satisfied by Phase 21 but never updated). Update the Traceability table.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §TYPE-02 — concrete config types in plugins; success criterion: no `config: Any` in plugin source
- `.planning/REQUIREMENTS.md` §TYPE-03 — Preset Protocol in core; `presets: list[Preset]` in all plugins
- `.planning/REQUIREMENTS.md` §QUAL-01 — no raw device-type string comparisons (Phase 20 closed equality checks; this phase closes assignment sites in DeviceAction construction)

### Phase 21 planning artifacts (being verified)
- `.planning/phases/21-concrete-types-plugin-boundary/21-01-PLAN.md` — original plan for Phase 21
- `.planning/phases/21-concrete-types-plugin-boundary/21-VALIDATION.md` — Nyquist validation from Phase 21

### Source files being changed
- `packages/rig-morningstar/src/rig_morningstar/device.py` — `presets: list[Any]` → `list[Preset]`; add `Preset` to import from `rig.engine.plugin`
- `packages/rig/src/rig/engine/plan/models.py` — add `ActionStatus` StrEnum; change `DeviceAction.device_type: str` → `DeviceType`; change `DeviceAction.status: Literal[...]` → `ActionStatus`
- `packages/rig/src/rig/engine/plan/compute.py` — update 3 `DeviceAction(...)` call sites to use enum members
- `packages/rig/src/rig/engine/apply.py` — update 1 `DeviceAction(...)` call site to use `DeviceType.CONTROLLER`

### Phase 21 verification output (new file)
- `.planning/phases/21-concrete-types-plugin-boundary/21-01-VERIFICATION.md` — to be written as part of this phase

### Existing enum pattern reference
- `packages/rig/src/rig/engine/plugin.py` lines 47-51 — `DeviceType(StrEnum)` definition; `ActionStatus` follows the same pattern in `plan/models.py`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DeviceType(StrEnum)` at `engine/plugin.py:47` — exact pattern to copy for `ActionStatus`
- `rig.engine.plugin.Preset(Protocol)` at `engine/plugin.py:115` — the Protocol `MC6Device.presets` should reference
- `MC6Device` already imports `DeviceType` from `rig.engine.plugin` — adding `Preset` to the same import is a one-liner

### Established Patterns
- `StrEnum` for domain enums (per CLAUDE.md and Phase 20 QUAL-02 decision) — `ActionStatus` is a new enum in the same style
- No backwards-compat shims — change the field type, fix call sites, done
- Pydantic `StrEnum` fields serialize to their string `.value` in JSON automatically — no custom serializer needed

### Integration Points
- `DeviceAction` is constructed in `compute.py` (3 sites) and `apply.py` (1 site); consumed by the plan output display in `cli/commands/plan.py` and by `apply.py`'s dispatch logic
- Any test that constructs `DeviceAction` with raw string `device_type` or `status` values will need updating to use enum members — check `test_plan.py` and `test_apply.py`
- Phase 21 VERIFICATION.md should grep for the 4 success criteria; the planner should include the actual grep commands and their expected zero-hit output

</code_context>

<specifics>
## Specific Ideas

- `ActionStatus` should live in `engine/plan/models.py` alongside `DeviceAction` — not in `engine/plugin.py` (that's the device protocol module, not the plan model module)
- When writing the Phase 21 VERIFICATION.md, run the 4 grep/file-existence checks live and record their actual output — same style as the Phase 20 VERIFICATION.md at `.planning/phases/20-quick-wins-dead-code/20-01-VERIFICATION.md`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 24-close-v1-4-gaps-phase-21-verification-mc6-preset-typing-qual*
*Context gathered: 2026-06-16*
