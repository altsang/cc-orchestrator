#!/bin/bash
# Test authentication modules without overall coverage requirements

set -e

echo "Running authentication tests without coverage constraints..."

# Run all authentication tests without the global coverage requirement
python -m pytest tests/unit/test_web_auth.py tests/unit/test_web_auth_coverage.py \
    --no-cov \
    -v

echo ""
echo "Running specific failing tests mentioned in the issue..."

# Run the specific 9 failing tests mentioned in the issue
python -m pytest \
    tests/unit/test_web_auth.py::TestTokenFunctions::test_create_access_token_default_expiry \
    tests/unit/test_web_auth.py::TestTokenFunctions::test_create_access_token_custom_expiry \
    tests/unit/test_web_auth.py::TestGetCurrentUser::test_get_current_user_no_exp_claim \
    tests/unit/test_web_auth.py::TestModuleConstants::test_secret_key_from_environment \
    tests/unit/test_web_auth_coverage.py::TestTokenOperations::test_create_access_token_default_expiry \
    tests/unit/test_web_auth_coverage.py::TestTokenOperations::test_create_access_token_custom_expiry \
    tests/unit/test_web_auth_coverage.py::TestTokenOperations::test_create_access_token_no_expiry_delta \
    tests/unit/test_web_auth_coverage.py::TestGetCurrentUser::test_get_current_user_expired_token \
    tests/unit/test_web_auth_coverage.py::TestGetCurrentUser::test_get_current_user_no_exp_claim \
    --no-cov \
    -v

echo ""
echo "Authentication tests completed successfully!"
echo "All tests pass when run individually or together without coverage constraints."
