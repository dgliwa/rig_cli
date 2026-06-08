---
status: complete
phase: 10-schema-loader-rewrite
source:
  - 10-PLAN.md
  - 10-SUMMARY.md
started: "2026-06-08T05:00:00Z"
updated: "2026-06-08T05:00:00Z"
---

## Current Test

[testing complete]

## Tests

### 1. Single-file rig.yaml loads correctly
expected: |
  `load_rig()` reads a single `rig.yaml` with a flat `devices` list.
  The loaded `Rig` has the correct `name`, `description`, and all three devices
  (mood, hx-stomp, mc6) populated.
result: pass

### 2. Signal chain from device list order
expected: |
  `Rig.signal_chain` is a list of device IDs in the order they appear in `rig.yaml`.
  No `signal-chain.yaml` file is read or required. Loading a rig with only `rig.yaml`
  (no signal-chain.yaml) succeeds and produces the correct chain order.
result: pass

### 3. Controller `composes` validation
expected: |
  A controller with `composes: [existing-device-id]` loads successfully.
  A controller with `composes: [nonexistent-id]` raises `MissingReferenceError`
  with a message mentioning the unknown device ID.
result: pass

### 4. Scenes extracted from controller config
expected: |
  Scenes defined inside a controller device's `config.scenes` are extracted into
  `Rig.scenes`. Each scene has the correct `name`, `description`, `presets` mapping,
  and `tags`. Controller-specific fields (bank, switch) remain in the device config only.
result: pass

### 5. Unknown config type produces clear error
expected: |
  A device with `config.type` set to a value that no plugin handles (e.g., `"nonexistent"`)
  produces a `ValidationError` with a message like
  `Unknown device config type 'nonexistent' — is the plugin registered?`
result: pass

### 6. Direct file path accepted
expected: |
  `load_rig()` accepts both a directory path (containing `rig.yaml`) and a direct path to
  `rig.yaml`. Both produce the same result.
result: pass

### 7. All tests pass
expected: |
  `uv run pytest packages/ -q --tb=short` passes with 260+ tests and all plugin tests passing.
result: pass

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
