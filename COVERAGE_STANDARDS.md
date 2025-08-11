# Coverage Measurement Standards

## Canonical Coverage Command

**ALWAYS** use this exact command for official coverage measurement:

```bash
# Official coverage measurement command
python -m pytest --tb=short
python -m coverage report
```

## Coverage Requirements

- **Target**: 90.00% minimum coverage
- **Current**: 90.008% (4486/4984 lines covered)
- **Tests**: 966 tests passing

## Common Issues

### ❌ Wrong: Running Individual Test Files
```bash
# This gives incorrect coverage (6-20%)
python -m pytest tests/unit/test_git_operations.py -v
```

### ✅ Correct: Running Full Test Suite
```bash
# This gives accurate coverage (90%+)
python -m pytest --tb=short
```

### ❌ Wrong: Different Coverage Configs
- Different pytest configurations
- Different coverage source paths
- Cached coverage data

### ✅ Correct: Standard Process
1. Clean run: `rm -f .coverage`
2. Full test suite: `python -m pytest --tb=short`
3. Coverage report: `python -m coverage report`

## Verification Protocol

Before reviewing coverage claims:

```bash
# 1. Clean state
git status
rm -f .coverage

# 2. Full test run
python -m pytest --tb=short

# 3. Get precise coverage
python -m coverage report | tail -1
python -c "covered=4486; total=4984; print(f'Precise: {covered/total*100:.6f}%')"
```

## Quality Gates

- ✅ **Type Safety**: `python -m mypy src/cc_orchestrator --no-error-summary`
- ✅ **Test Coverage**: `python -m coverage report` (≥90%)
- ✅ **Test Pass Rate**: `python -m pytest --tb=short` (100%)
- ✅ **Linting**: All quality checks pass

## Current Status ✅

- **Coverage**: 90.008% (4486/4984 lines covered)
- **Tests**: 966 passing, 4 warnings
- **mypy**: Zero errors
- **Last Verified**: August 11, 2025
