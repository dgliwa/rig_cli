---
status: complete
phase: 09-core-model-cleanup
source:
  - 09-01-SUMMARY.md
  - 09-02-SUMMARY.md
  - 09-03-SUMMARY.md
  - 09-04-SUMMARY.md
started: 2026-06-08T08:00:00Z
updated: 2026-06-08T08:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Load and validate fixture rig config
expected: `rig validate` against the sample_rig fixture exits 0 and prints validation summary.
result: pass

### 2. Plan from fixture rig config
expected: `rig plan` against the sample_rig fixture exits 0 and prints a plan summary including scenes and actions.
result: pass

### 3. Status from fixture rig config
expected: `rig status` against the sample_rig fixture exits 0 and prints a device/status table.
result: pass

### 4. Generate MC6 from fixture rig config
expected: `rig generate mc6` against the sample_rig fixture exits 0 and writes MC6 bank JSON files.
result: pass

### 5. Model structure — Device has no manufacturer/model fields
expected: Creating a Device from Python shows no `manufacturer` or `model` in `model_fields`.
result: pass

### 6. Backward compat — YAML with manufacturer/model still loads
expected: A YAML file containing `manufacturer:` and `model:` fields loads without error (fields silently ignored).
result: pass

### 7. Signal chain is list of strings
expected: `Rig.signal_chain` is a `list[str]` — items are device ID strings, not objects.
result: pass

### 8. Scene has no mc6 fields
expected: Scene model has no `mc6_bank` or `mc6_switch` fields.
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
