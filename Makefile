.PHONY: install test lint build clean lock

# ─── Dev ─────────────────────────────────────────────────────────────────────

install:           ## Install dependencies and package (editable)
	uv sync

lock:              ## Re-lock dependencies
	uv lock

# ─── Quality ─────────────────────────────────────────────────────────────────

test:              ## Run all tests
	uv run pytest tests/ -v

lint:              ## Lint with ruff
	uv run ruff check src/

format:            ## Format with ruff
	uv run ruff format src/

# ─── Build / Package ─────────────────────────────────────────────────────────

build:             ## Build wheel + sdist
	uv build

publish:           ## Publish to PyPI
	uv publish

# ─── Install ──────────────────────────────────────────────────────────────────

tool-install:      ## Install as a globally-available CLI tool (like pipx)
	uv tool install .

# ─── Clean ────────────────────────────────────────────────────────────────────

clean:             ## Remove build/dist artifacts
	rm -rf dist/ build/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
