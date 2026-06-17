# Phase 27: Editor Protocol, CLI Surface & YAML Writer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-17
**Phase:** 27-editor-protocol-cli-yaml-writer
**Areas discussed:** EditorProtocol shape, YAML round-trip strategy, EditContext design, Phase 27 editor interaction boundary

---

## EditorProtocol Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Add edit() to Device Protocol directly | Every plugin must implement edit(); simplest dispatch | |
| Separate EditorProtocol (companion) | Device Protocol unchanged; plugins opt in via isinstance check | ✓ |
| Optional method on Device Protocol (default stub) | Default no-op body; plugins override if they support editing | |

**User's choice:** Separate EditorProtocol (companion)
**Notes:** Device Protocol stays unchanged — EditorProtocol is a companion. isinstance dispatch. Unsupported devices print a warning and exit cleanly (non-error exit code).

---

## YAML Round-Trip Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| ruamel.yaml | Preserves comments, order, formatting; new dependency | ✓ |
| PyYAML dump | Already a dependency, loses formatting | |
| Targeted patch | Parse → mutate dict → write; same loss of formatting as PyYAML | |

**User's choice:** ruamel.yaml

**Write atomicity sub-question:**

| Option | Description | Selected |
|--------|-------------|----------|
| Temp file + os.rename() on confirm | Atomic on POSIX; crash-safe | |
| Keep snapshot in memory, write only on confirm | Simpler; no temp file; not crash-safe | ✓ |

**Notes:** Memory-only write is sufficient for Phase 27. Crash-safe rename is a future hardening step.

---

## EditContext Design

| Option | Description | Selected |
|--------|-------------|----------|
| New EditContext dataclass | Purpose-built; only edit-relevant fields | ✓ |
| Reuse DeviceApplyContext | Less code; carries irrelevant midi/state fields | |

**User's choice:** New EditContext dataclass

**Fields selected (multiSelect):** config_path: Path, dry_run: bool, confirmation_io: ConfirmationIO, rig: Rig

**Notes:** All four fields. Clean separation from apply context.

---

## Phase 27 Editor Interaction Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Generic value-prompt loop | Loops through preset fields, prompts via ConfirmationIO | |
| Skeleton only — enter + save/discard immediately | Structural only; no value prompts | ✓ |
| Plugin stub returns no-op edit session | EditorProtocol wired but no plugin implements it | |

**User's choice:** Skeleton only

**Plugin stubs sub-question:**

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 27 adds skeleton edit() stubs to CBA + MIDI plugins | Return current preset values; Phase 28 replaces | ✓ |
| Phase 27 skips stubs; engine tests use FakeEditorPlugin | No production plugin until Phase 28 | |

**Notes:** User first asked to verify Phase 28 scope. Phase 28 (EDIT-03/06) owns real plugin behavior. Phase 27 stubs needed for end-to-end testability of success criterion 2. Analog plugin does NOT get a stub — it doesn't implement EditorProtocol until Phase 28.

---

## Claude's Discretion

- Skeleton stub message format — chosen as `"Editor mode: <device-id>/<preset-id> (no interactive editing available — Phase 28 will add this)"`
- ruamel.yaml usage pattern — `YAML(typ='rt')` round-trip mode

## Deferred Ideas

- Crash-safe atomic write (temp file + os.rename()) — Phase 27 ships memory-only; rename is future hardening
- HX Stomp editor mode — not in Phase 27 or 28 scope
- Analog editor stub — Phase 28 adds this (EDIT-06)
