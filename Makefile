.PHONY: help install install-dev test test-cov lint format type-check clean build docs
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install the package
	pip install -e .

install-dev: ## Install development dependencies
	pip install -e ".[dev]"
	pre-commit install

test: ## Run tests
	pytest tests/ -v

test-cov: ## Run tests with coverage
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=90

lint: ## Run linting (ruff)
	ruff check src/ tests/

lint-fix: ## Fix linting issues
	ruff check --fix src/ tests/

format: ## Format code (black)
	black src/ tests/

format-check: ## Check code formatting
	black --check src/ tests/

type-check: ## Run type checking (mypy)
	mypy src/

quality: ## Run all quality checks
	make format-check
	make lint
	make type-check
	make test-cov

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build: clean ## Build the package
	python -m build

docs: ## Generate documentation
	@echo "Documentation generation not yet implemented"

ci: ## Run CI pipeline locally
	make quality
	make build

pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files
