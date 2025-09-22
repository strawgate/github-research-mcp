.PHONY: format check lint test all clean help

# Alias for check-fix
lint:
	uv run ruff format
	uv run ruff check --fix

# Run tests with pytest
test:
	uv run pytest

# Clean up cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

# Show available targets
help:
	@echo "Available targets:"
	@echo "  lint        - Format and check-fix"
	@echo "  test        - Run tests with pytest"
	@echo "  clean       - Clean up cache files"
	@echo "  help        - Show this help message"