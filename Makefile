.PHONY: help install lock test lint lint-all format format-all pre-commit-install pre-commit-check build publish tool-install clean

# ─── Help ─────────────────────────────────────────────────────────────────────

help:              ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

# ─── Dev ─────────────────────────────────────────────────────────────────────

install:           ## Install dependencies and package (editable)
	uv sync

lock:              ## Re-lock dependencies
	uv lock

# ─── Quality ─────────────────────────────────────────────────────────────────

test:              ## Run all tests
	uv run pytest -v

lint:              ## Lint source with ruff
	uv run ruff check packages/

lint-all:          ## Lint src + tests with ruff
	uv run ruff check packages/

format:            ## Format source with ruff
	uv run ruff format packages/

format-all:        ## Format src + tests with ruff
	uv run ruff format packages/

pre-commit-install: ## Install pre-commit hooks
	uv run pre-commit install

pre-commit-check:  ## Run all pre-commit hooks against all files
	uv run pre-commit run --all-files

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
