# Contributing to CC-Orchestrator

Thank you for your interest in contributing to CC-Orchestrator! This document provides guidelines and instructions for contributors.

## Development Setup

### Prerequisites
- Python 3.9 or higher
- Git
- Make (optional, but recommended)

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/altsang/cc-orchestrator.git
   cd cc-orchestrator
   ```

2. **Install development dependencies**
   ```bash
   make install-dev
   # OR manually:
   pip install -e ".[dev]"
   pre-commit install
   ```

3. **Verify setup**
   ```bash
   make test
   ```

## Development Workflow

### Code Quality Standards

We maintain high code quality standards:

- **Test Coverage**: Minimum 90% coverage required
- **Type Hints**: All functions must have proper type annotations
- **Documentation**: All public APIs must be documented
- **Linting**: Code must pass ruff linting
- **Formatting**: Code must be formatted with black

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write code following our standards
   - Add comprehensive tests
   - Update documentation if needed

3. **Run quality checks**
   ```bash
   make quality  # Runs formatting, linting, type-checking, and tests
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: your descriptive commit message"
   ```

5. **Push and create PR**
   ```bash
   git push -u origin feature/your-feature-name
   # Create PR via GitHub UI
   ```

### Commit Message Convention

We follow conventional commit format:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test additions/modifications
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

### Testing Requirements

- **Unit Tests**: Required for all new functionality
- **Integration Tests**: Required for complex features
- **Coverage**: Must maintain minimum 90% coverage
- **Async Testing**: Use pytest-asyncio for async code

Example test structure:
```python
class TestNewFeature:
    def test_basic_functionality(self):
        # Test basic case

    def test_edge_cases(self):
        # Test edge cases

    def test_error_handling(self):
        # Test error conditions
```

### Code Review Process

1. **Automated Checks**: All CI checks must pass
2. **Peer Review**: At least one approval required
3. **Quality Gates**:
   - Test coverage ≥ 90%
   - All linting passes
   - Type checking passes
   - Documentation updated

### Available Make Commands

```bash
make help           # Show all available commands
make install        # Install package
make install-dev    # Install with dev dependencies
make test           # Run tests
make test-cov       # Run tests with coverage report
make lint           # Run linting
make format         # Format code
make type-check     # Run type checking
make quality        # Run all quality checks
make clean          # Clean build artifacts
make build          # Build package
make ci             # Run full CI pipeline locally
```

## Architecture Guidelines

### Project Structure
```
src/cc_orchestrator/
├── cli/           # Command-line interface
├── core/          # Core orchestration logic
├── database/      # Database models and operations
├── web/           # Web interface
├── integrations/  # External service integrations
└── utils/         # Utility functions

tests/
├── unit/          # Unit tests
├── integration/   # Integration tests
└── fixtures/      # Test fixtures and data
```

### Design Principles

1. **Separation of Concerns**: Each module has a single responsibility
2. **Dependency Injection**: Use dependency injection for testability
3. **Async by Default**: All I/O operations should be async
4. **Type Safety**: Comprehensive type hints throughout
5. **Error Handling**: Graceful error handling with proper logging

## Security Guidelines

- Never commit secrets or credentials
- Use environment variables for configuration
- Follow security best practices for external integrations
- Run security checks: `bandit -r src/`

## Documentation

- Update docstrings for all public functions
- Update README.md for user-facing changes
- Update this CONTRIBUTING.md for process changes
- Add examples for new features

## Getting Help

- **GitHub Issues**: Report bugs and request features
- **Discussions**: Ask questions and discuss ideas
- **Discord**: Join our development community [link-to-discord]

## Recognition

Contributors will be recognized in:
- AUTHORS.md file
- Release notes
- Git commit co-authoring

Thank you for contributing to CC-Orchestrator! 🚀
