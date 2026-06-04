# Testing Patterns

**Analysis Date:** 2026-06-03

## Test Framework

**Runner:**
- pytest
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`
- `testpaths = ["tests"]`

**Assertion Library:**
- pytest built-in `assert` statements (no separate assertion library)

**Run Commands:**
```bash
make test                        # uv run pytest tests/ -v
uv run pytest tests/ -q          # quiet output
uv run pytest --cov              # coverage (pytest-cov installed)
```

## Test File Organization

**Location:** All tests in `tests/` at project root (not co-located with source).

**Naming:** `test_<module>.py` matching the module under test:
- `tests/test_models.py` — `src/rig/models/`
- `tests/test_loader.py` — `src/rig/config/loader.py`
- `tests/test_plan.py` — `src/rig/engine/plan.py`
- `tests/test_appliers.py` — `src/rig/engine/appliers/`
- `tests/test_midi_adapter.py` — `src/rig/midi/adapter.py`
- `tests/test_mc6_generator.py` — `src/rig/generators/mc6_presets.py`
- `tests/test_apply.py` — `src/rig/engine/apply.py`
- `tests/test_diff.py` — `src/rig/engine/diff.py`
- `tests/test_catalog.py` — catalog data + integration smoke
- `tests/test_cli.py` — CLI entry point
- `tests/test_logging.py` — log setup
- `tests/test_mc6_sysex.py` — MC6 sysex generation

**Fixtures directory:** `tests/fixtures/sample_rig/` — full YAML rig for loader integration tests.

## Test Structure

**Suite Organization:**

All tests use `class`-based grouping with `Test` prefix:
```python
class TestPedalModels:
    def test_pedal_definition_round_trips(self): ...

class TestPresetModels:
    def test_analog_preset_round_trips_knob_values(self): ...
```

Test method names are full sentences describing behavior: `test_dry_run_skips_prompt_and_returns_skipped`, `test_connect_shares_port_by_name`.

**No `unittest.TestCase` inheritance** — pure pytest classes.

**Private builder helpers** are module-level functions (not fixtures) prefixed with `_`:
```python
def _make_ctx(dry_run: bool = False, connected: set[str] | None = None) -> ApplyContext:
    midi = MagicMock()
    return ApplyContext(dry_run=dry_run, midi=midi, ...)

def _analog_action(device: str = "fuzz", preset_name: str = "Noon") -> DeviceAction:
    return DeviceAction(...)
```

**Class-level applier instances** for stateless objects:
```python
class TestAnalogApplier:
    applier = AnalogApplier()
```

## Fixtures

**pytest fixtures** used for stateful setup (filesystem, MIDI adapter):

```python
@pytest.fixture
def rig_dir(tmp_path):
    d = tmp_path / "rig"
    d.mkdir()
    _write(d, "rig.yaml", "name: test-rig\n...")
    return d

@pytest.fixture
def midi():
    with patch("rig.midi.adapter._HAS_MIDO", True):
        yield MidiManager()
```

- `tmp_path` (built-in pytest) used extensively for filesystem tests
- Fixtures do not use `conftest.py` — they are defined in the same file they're used
- The `tests/fixtures/sample_rig/` directory provides a real YAML rig used by `test_catalog.py` via the string path `FIXTURE_PATH = "tests/fixtures/sample_rig"`

## Mocking

**Framework:** `unittest.mock` — `MagicMock`, `patch`

**MIDI hardware is always mocked.** The `mido` backend is patched at the module flag level:
```python
with patch("rig.midi.adapter._HAS_MIDO", True):
    yield MidiManager()
```

Individual mido calls are patched per-test:
```python
with patch("rig.midi.adapter.mido.open_output", return_value=fake_port):
    midi.connect("P", "hx-stomp")
```

**User input (`builtins.input`) is patched** for all interactive prompt tests:
```python
with patch("builtins.input", return_value="c"):
    result = self.applier.apply_scene(action, ctx)

with patch("builtins.input", side_effect=["r", "c"]):  # multi-step interaction
    result = self.applier.apply_scene(action, ctx)
```

**`MagicMock()` for MIDI manager** in applier tests — passed directly into `ApplyContext`:
```python
def _make_ctx(...) -> ApplyContext:
    midi = MagicMock()
    return ApplyContext(dry_run=dry_run, midi=midi, ...)
```
Assertions then use `ctx.midi.send_program_change.assert_called_once_with(...)`.

## Test Types

**Unit tests (majority):**
- Model construction and validation: `test_models.py`
- Engine plan logic with in-memory state: `test_plan.py`
- Applier behavior with mocked MIDI and input: `test_appliers.py`
- MIDI adapter with mocked mido: `test_midi_adapter.py`

**Integration tests:**
- Full loader + validation from filesystem YAML: `test_loader.py` (uses `tmp_path` + `_write` helpers)
- Catalog + loader + plan + generator smoke: `test_catalog.py` (uses `tests/fixtures/sample_rig/`)

**No E2E tests.** CLI (`test_cli.py`) is present but scope unclear from exploration.

## Error Testing

Pydantic validation errors tested with `pytest.raises(ValidationError)`:
```python
def test_scene_rejects_invalid_switch(self):
    with pytest.raises(ValidationError):
        Scene(name="bad", presets={"hx-stomp": "x"}, mc6_switch="Z")
```

Domain errors tested with custom exception types:
```python
with pytest.raises(FileNotFoundError_):
    load_rig(str(rig_dir))

with pytest.raises(MissingReferenceError):
    load_rig(str(rig_dir))

with pytest.raises(MidiConnectionError, match="Could not open"):
    midi.connect("Busy Port", "device-x")
```

`match=` used on `pytest.raises` when the message content matters.

## Coverage Gaps

- `src/rig/engine/apply.py` has a dedicated test file (`test_apply.py`) but integration coverage of the full apply loop with real state is unclear
- `src/rig/cli.py` has `test_cli.py` but CLI command coverage depth is unknown
- `src/rig/ingest/` directory is not present in `tests/` test files listed — ingest module coverage unknown
- `src/rig/engine/appliers/registry.py` and `src/rig/engine/appliers/mc6.py` have no dedicated test files visible
- One test method is missing the `test_` prefix and will be silently skipped: `invalid_control_rejected` in `tests/test_models.py` line 44

## Async / Hardware

- No async tests. No `pytest-asyncio`.
- All hardware interaction (MIDI) is synchronous and mocked via `unittest.mock.patch`.
- No tests are marked `@pytest.mark.skip` for hardware absence — the `_HAS_MIDO` flag handles graceful degradation.

---

*Testing analysis: 2026-06-03*
