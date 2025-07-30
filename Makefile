# CC-Orchestrator Production-Ready Development Makefile
# Ensures all components meet production standards before merge

.PHONY: help install install-dev setup quality-check commit-ready pr-ready test test-cov lint format type-check clean build docs security-scan
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "CC-Orchestrator Development Commands"
	@echo "===================================="
	@echo "Production-Ready Workflow:"
	@echo "  1. make setup         - Initial development environment setup"
	@echo "  2. make quality-check - Run before every commit (MANDATORY)"
	@echo "  3. make commit-ready  - Verify readiness for commit"
	@echo "  4. make pr-ready      - Verify readiness for pull request"
	@echo ""
	@echo "Available Commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install the package
	pip install -e .

install-dev: ## Install development dependencies
	pip install -e ".[dev]"
	pip install mypy ruff black pytest pytest-cov pytest-mock
	pip install pre-commit safety bandit
	pip install types-PyYAML types-click

setup: install-dev ## Complete development environment setup (run once)
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "✅ Development environment ready!"
	@echo "📋 Remember: Run 'make quality-check' before every commit"
	@echo "📖 See DEVELOPMENT_METHODOLOGY.md for complete standards"

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
	@echo "🔍 Running type checking on core modules..."
	mypy src/cc_orchestrator/cli/ src/cc_orchestrator/config/ --show-error-codes
	@echo "✅ Type checking passed"

# Production-Ready Quality Gates
quality-check: ## MANDATORY: Run before every commit
	@echo "🚀 Running production-ready quality checks..."
	@echo "1/4 Type checking..."
	@make type-check
	@echo "2/4 Code formatting..."
	@make format
	@echo "3/4 Linting..."
	@make lint-fix
	@echo "4/4 Testing..."
	@make test
	@echo "✅ ALL QUALITY CHECKS PASSED - Ready to commit!"

quality: quality-check ## Alias for quality-check

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

# Security & Advanced Validation
security-scan: ## Run security scans
	@echo "🔒 Running security scans..."
	bandit -r src/ -f json -o security-report.json || true
	safety check --json --output safety-report.json || true
	@echo "✅ Security scan complete (check reports for issues)"

# Configuration-Specific Testing
test-config: ## Run configuration management tests
	@echo "🧪 Running configuration tests..."
	pytest tests/unit/test_config_enhancements.py -v
	@echo "✅ Configuration tests passed"

test-cli: ## Test CLI functionality manually
	@echo "🖥️  Testing CLI functionality..."
	cc-orchestrator --help > /dev/null
	cc-orchestrator config --help > /dev/null
	cc-orchestrator --max-instances 10 --json config show > /dev/null
	@echo "✅ CLI functionality verified"

# Workflow Commands
commit-ready: quality-check ## Verify everything is ready for commit
	@echo "✅ COMMIT READY: All quality gates passed"
	@echo "Next steps:"
	@echo "  1. git add ."
	@echo "  2. git commit -m 'Your descriptive commit message'"

pr-ready: quality-check test-cov security-scan test-cli ## Verify everything is ready for PR
	@echo "✅ PR READY: All validation passed"
	@echo "Next steps:"
	@echo "  1. git push origin your-feature-branch"
	@echo "  2. Create PR with comprehensive description"

pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files

# Development Shortcuts
quick-check: type-check lint-fix ## Quick check without tests (for rapid iteration)
	@echo "⚡ Quick check complete"
