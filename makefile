.PHONY: format check lint test all clean help

# Default target
all: format check test

# Format code with ruff
format:
	uv run ruff format

# Check code with ruff (without fixing)
check:
	uv run ruff check

# Check and fix code with ruff
check-fix:
	uv run ruff check --fix

# Alias for check-fix
lint: check-fix

# Run tests with pytest
test:
	uv run pytest

# Run tests with verbose output
test-verbose:
	uv run pytest -v

# Run tests with coverage
test-coverage:
	uv run pytest --cov

# Format, check-fix, and test in sequence
ci: format check-fix test

# Clean up cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

# Show available targets
help:
	@echo "Available targets:"
	@echo "  format      - Format code with ruff"
	@echo "  check       - Check code with ruff (no fixes)"
	@echo "  check-fix   - Check and fix code with ruff"
	@echo "  lint        - Alias for check-fix"
	@echo "  test        - Run tests with pytest"
	@echo "  test-verbose - Run tests with verbose output"
	@echo "  test-coverage - Run tests with coverage"
	@echo "  ci          - Format, check-fix, and test"
	@echo "  clean       - Clean up cache files"
	@echo "  all         - Format, check, and test (default)"
	@echo "  help        - Show this help message"