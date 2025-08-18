# Authentication Test Coverage Fix

## Problem
The authentication tests were failing when run individually or as part of specific test selections due to the project's 74% global coverage requirement. When running only auth tests, the coverage calculation included the entire codebase but only executed the auth module tests, resulting in very low overall coverage (~4%) that failed the 74% threshold.

## Solution
This fix provides multiple ways to run the problematic authentication tests without triggering coverage failures:

### Method 1: Using the Auth Test Runner Script
```bash
python run_auth_tests.py
```

This script runs all auth tests marked with `@pytest.mark.auth` without coverage requirements.

### Method 2: Using Pytest Markers Directly
```bash
# Run all auth-marked tests without coverage
python -m pytest -m auth --no-cov -v

# Run specific auth test without coverage
python -m pytest tests/unit/test_web_auth.py::TestTokenFunctions::test_create_access_token_default_expiry --no-cov -v
```

### Method 3: Disable Coverage for Individual Tests
For any individual auth test that's failing due to coverage:
```bash
python -m pytest <test_path> --no-cov -v
```

## Affected Tests
The following 9 tests were failing due to coverage requirements and are now fixed:

1. `tests/unit/test_web_auth.py::TestTokenFunctions::test_create_access_token_default_expiry`
2. `tests/unit/test_web_auth.py::TestTokenFunctions::test_create_access_token_custom_expiry`
3. `tests/unit/test_web_auth.py::TestGetCurrentUser::test_get_current_user_no_exp_claim`
4. `tests/unit/test_web_auth.py::TestModuleConstants::test_secret_key_from_environment`
5. `tests/unit/test_web_auth_coverage.py::TestTokenOperations::test_create_access_token_default_expiry`
6. `tests/unit/test_web_auth_coverage.py::TestTokenOperations::test_create_access_token_custom_expiry`
7. `tests/unit/test_web_auth_coverage.py::TestTokenOperations::test_create_access_token_no_expiry_delta`
8. `tests/unit/test_web_auth_coverage.py::TestGetCurrentUser::test_get_current_user_expired_token`
9. `tests/unit/test_web_auth_coverage.py::TestGetCurrentUser::test_get_current_user_no_exp_claim`

## Implementation Details

### Pytest Markers
- Added `@pytest.mark.auth` to the specific failing tests
- Added "auth: Authentication module tests" to pytest markers in pyproject.toml

### Test Runner Script
- `run_auth_tests.py` - Runs auth tests without global coverage requirements
- Uses `--override-ini=addopts=` to clear default coverage settings
- Uses `--no-cov` to completely disable coverage
- Uses `-m auth` to run only auth-marked tests

### Coverage Configuration
The full test suite still maintains the 74% coverage requirement. Only when running auth tests individually or via the special runner do we bypass coverage.

## Usage in CI/CD
For CI/CD systems, use the test runner script:
```bash
python run_auth_tests.py
```

This ensures the auth tests pass while maintaining test isolation and not affecting the main test suite's coverage requirements.

## Development Workflow
- Full test suite: `python -m pytest` (maintains 74% coverage requirement)
- Auth tests only: `python run_auth_tests.py` (no coverage requirement)
- Individual tests: Add `--no-cov` flag when testing auth modules
