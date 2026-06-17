# Phase 24: Close v1.4 gaps: Phase 21 verification, MC6 preset typing, QUAL-01 DeviceAction - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-16
**Phase:** 24-close-v1-4-gaps-phase-21-verification-mc6-preset-typing-qual
**Areas discussed:** MC6 preset typing, DeviceAction.device_type field, Phase 21 VERIFICATION.md scope

---

## MC6 preset typing

| Option | Description | Selected |
|--------|-------------|----------|
| list[Preset] (always empty) | Change to list[Preset] with Field(default_factory=list). MC6 never has presets — the Protocol is satisfied, the code is honest. | ✓ |
| list[Never] | Use typing.Never to signal always-empty. Protocol conformance requires list[Preset] so Never would need a cast. | |
| Leave as list[Any] + comment | Add a comment explaining MC6 has no presets. Does NOT close Phase 21 success criterion #3. | |

**User's choice:** `list[Preset]` (always empty)
**Notes:** Direct import from `rig.engine.plugin` — same import that already brings in `DeviceType`, `DeviceApplyContext`, etc. No TYPE_CHECKING guard needed.

---

## DeviceAction.device_type field

| Option | Description | Selected |
|--------|-------------|----------|
| DeviceType enum field | Change to `device_type: DeviceType`. Construction sites use enum members. Pydantic serializes StrEnum as .value — no JSON change. | ✓ |
| Keep str, use .value consistently | Leave field as str but change hardcoded strings to DeviceType.ANALOG.value at call sites. Weaker — field still accepts any string. | |
| Literal['analog', 'digital', 'controller', 'modeler'] | Narrow str to Literal. Documents valid values but doesn't enforce the enum. | |

**User's choice:** `DeviceType` enum field
**Notes:** Three construction sites: `compute.py:93`, `compute.py:118`, `apply.py:165`.

---

## DeviceAction.status field (emerged during DeviceAction discussion)

| Option | Description | Selected |
|--------|-------------|----------|
| New ActionStatus StrEnum | `class ActionStatus(StrEnum)` with CONFIGURE, VERIFY, ANALOG. Parallel to DeviceType. Lives in `engine/plan/models.py`. | ✓ |
| Literal with enum values | Keep Literal but reference DeviceType where possible. Awkward — configure/verify aren't DeviceType values. | |

**User's choice:** `ActionStatus(StrEnum)` — same pattern as `DeviceType`
**Notes:** "analog" in status means "manual/human interaction required", not the DeviceType.ANALOG per se, but having the enum makes this explicit and consistent.

---

## Phase 21 VERIFICATION.md scope

| Option | Description | Selected |
|--------|-------------|----------|
| Fix MC6 first, then write VERIFICATION.md | Close criterion #3 first so all 4 criteria pass. VERIFICATION.md is a clean post-hoc audit. | ✓ |
| Write VERIFICATION.md acknowledging the MC6 gap | Write now, document criterion #3 as PARTIAL. Splits the story. | |

**User's choice:** Fix MC6 first, then write VERIFICATION.md

**REQUIREMENTS.md update:**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — mark TYPE-02/TYPE-03 complete in this phase | They were satisfied by Phase 21 but never updated. Correct the record. | ✓ |
| No — historical record issue only | | |

**User's choice:** Update REQUIREMENTS.md as part of Phase 24 work.

---

## Claude's Discretion

None — all areas had clear user preferences.

## Deferred Ideas

None — discussion stayed within phase scope.
