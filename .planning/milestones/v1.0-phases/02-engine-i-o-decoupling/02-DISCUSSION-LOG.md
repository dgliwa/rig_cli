# Phase 2: Engine I/O Decoupling - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-04
**Phase:** 02-engine-i-o-decoupling
**Areas discussed:** ConfirmationIO shape, Adapter file location, confirmation_io default, InMemoryPromptAdapter shape

---

## ConfirmationIO shape

| Option | Description | Selected |
|--------|-------------|----------|
| One per function (5 methods) | Mirror the existing interaction module exactly — 5 methods (prompt_analog, prompt_device, prompt_cba_channel, prompt_cba_preset, prompt_cba_register). Call sites map 1:1. | ✓ |
| Three grouped (analog, midi, cba) | Fold 3 CBA functions into one prompt_cba(device, step, **kwargs). Reduces Protocol surface but adds a step discriminator. | |
| You decide | Claude picks based on cleanest fake and least applier churn. | |

**User's choice:** One per function (5 methods)
**Notes:** Cleanest mapping; no abstraction overhead.

### MidiConnectionIO sub-question

| Option | Description | Selected |
|--------|-------------|----------|
| Prompt-only (returns port name) | MidiConnectionIO wraps user prompt, returns chosen port name. apply_plan opens port separately. | ✓ |
| Full connect (prompt + open) | MidiConnectionIO.connect() prompts AND opens port, returning a connected MidiManager. | |
| You decide | Claude picks based on what makes apply_plan cleanest to test. | |

**User's choice:** Prompt-only
**Notes:** Clean separation of I/O concerns.

---

## Adapter file location

| Option | Description | Selected |
|--------|-------------|----------|
| engine/ports.py alongside Protocols | Protocols and production adapters in one file. Single source of truth. | ✓ |
| Separate engine/adapters.py | Protocols in ports.py, adapters in adapters.py. | |
| Inline in cli.py | Adapters defined locally in cli.py as closures. Keeps engine pure but untestable second entry points. | |

**User's choice:** engine/ports.py alongside Protocols
**Notes:** One file to read to understand the full I/O seam.

---

## confirmation_io default

| Option | Description | Selected |
|--------|-------------|----------|
| Optional (None default) | field(default=None). Appliers check before calling; fallback to direct interaction calls. | |
| Required (no default) | Callers must always pass it. DEC-04 and DEC-07 land together atomically. | ✓ |
| Default to StandardConfirmationIO() | field(default_factory=StandardConfirmationIO). No fallback branching but tests need explicit override. | |

**User's choice:** Required (no default)
**Notes:** DEC-04 and DEC-07 land in same phase — atomic update is fine.

### apply_plan params sub-question

| Option | Description | Selected |
|--------|-------------|----------|
| Required (no defaults) | Consistent with confirmation_io decision. | ✓ |
| Optional with None defaults | Useful for partial mock integration tests. | |

**User's choice:** Required (no defaults)

---

## InMemoryPromptAdapter shape

| Option | Description | Selected |
|--------|-------------|----------|
| Configurable default + per-call sequence | InMemoryPromptAdapter(default='confirm') with optional side_effect list. Mirrors Mock.side_effect semantics. | ✓ |
| Always-confirm only | Fake always returns 'confirm'. Tests needing 'skip'/'quit' still use patch(). | |
| Full recording fake | Records every call AND has configurable responses. More powerful but adds test complexity. | |

**User's choice:** Configurable default + per-call sequence
**Notes:** Matches existing patch(side_effect=[...]) test patterns exactly.

### InMemoryStateAdapter sub-question

| Option | Description | Selected |
|--------|-------------|----------|
| Store only (no recording) | Holds RigState in memory; tests assert on resulting state. | ✓ |
| Store + count writes | Also tracks write_count for DEC-06 assertions. | |

**User's choice:** Store only (no recording)

---

## Claude's Discretion

None — all areas had explicit user selections.

## Deferred Ideas

None — discussion stayed within phase scope.
