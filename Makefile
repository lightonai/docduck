# Convenience targets for development.

.PHONY: format lint test check install

install:
	uv pip install -e ".[dev]"

format:
	ruff format src/ tests/

lint:
	ruff check src/ tests/

# Check that code is formatted and lint-clean without modifying.
check:
	ruff format --check src/ tests/
	ruff check src/ tests/

test:
	pytest tests/ -q

# Format, lint, and test. Run before committing.
all: format lint test
