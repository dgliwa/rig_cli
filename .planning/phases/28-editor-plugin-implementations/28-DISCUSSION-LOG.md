# Phase 28: Editor Plugin Implementations - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-17
**Phase:** 28-editor-plugin-implementations
**Areas discussed:** CC control navigation UX, Live CC send timing, Analog editor flow, HX Stomp scope

---

## CC Control Navigation UX

| Option | Description | Selected |
|--------|-------------|----------|
| Sequential prompt-per-control | Walk through each control one-by-one; enter or skip | |
| Named control entry loop | Show all controls upfront; user types `<name> <value>`; loop until `done` | ✓ |
| Show all, edit by number | Numbered list; pick a number, enter value, list reprints | |

**User's choice:** Named control entry loop

---

### Display upfront

| Option | Description | Selected |
|--------|-------------|----------|
| Full control list with current values | Name, CC number, range, and current value | ✓ |
| Compact summary: name + current value only | Skip CC numbers and ranges | |
| Just the prompt — no upfront list | No listing; user expected to know control names | |

**User's choice:** Full control list with current values

---

### Input errors

| Option | Description | Selected |
|--------|-------------|----------|
| Print error, re-prompt same control | Error message then immediately re-prompt | ✓ |
| Print error, continue to next control | Error shown, control stays unchanged, advance | |
| Print error, let user retry / skip / quit | Offer choice after error | |

**User's choice:** Print error, re-prompt same control

---

## Live CC Send Timing

| Option | Description | Selected |
|--------|-------------|----------|
| Immediately on each valid value entry | CC fires as user enters each value — live preview | ✓ |
| Only on confirm/save | CC queued; device hears nothing until save | |

**User's choice:** Immediately on each valid value entry

---

### Discard behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Don't reset — device heard changes, rig.yaml stays clean | File unchanged; device state reflects last edited values | ✓ |
| Re-send original values on discard | MIDI rollback to pre-edit state | |

**User's choice:** Don't reset — rig.yaml is the source of truth; device CC state is acceptable to leave as-is

---

## Analog Editor Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Same named-entry loop as CC plugins (no MIDI sent) | Consistent UX; show all keys + current values; `<key> <value>`; loop until `done` | ✓ |
| Sequential one-by-one prompt | Walk each key in order; always visits every control | |
| You decide — keep consistent with CC flow | Defer to Claude | |

**User's choice:** Same named-entry loop — consistency across device types matters

---

### Analog validation

| Option | Description | Selected |
|--------|-------------|----------|
| Use existing values keys as valid names — no range validation | Accept keys already in preset; unknown key → error + re-prompt | ✓ |
| Accept any key/value — validate at rig validate time | No front-line validation during editing | |

**User's choice:** Validate against existing keys; no range validation (no catalog for analog)

---

## HX Stomp Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Leave HX out — follow REQUIREMENTS.md (EDIT-03 is CC-based only) | HX does not implement EditorProtocol; shows "does not support editing" warning | |
| Add a skeleton stub like CBA/MIDI got in Phase 27 | `edit()` stub prints placeholder, returns current values; future phase fills in | ✓ |
| Clarify ROADMAP.md — remove HX from Phase 28 description | Update roadmap, exclude HX entirely | |

**User's choice:** Add HX skeleton stub — consistent with how Phase 27 handled CBA/MIDI

---

## Claude's Discretion

- Control name matching: exact vs case-insensitive — either is fine; match catalog key format
- HX stub message wording — follow Phase 27 CBA stub pattern

## Deferred Ideas

- HX live CC/SysEx editing — future milestone
- MIDI rollback on discard — possible future hardening option
- Fuzzy control name matching — not a stated requirement
