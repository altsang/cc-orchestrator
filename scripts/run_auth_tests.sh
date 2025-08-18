#!/bin/bash
# Script to run auth tests without coverage constraints
# This is needed because auth tests require special environment setup
# that conflicts with normal coverage measurement

echo "Running auth tests without coverage..."

# Run all auth tests without coverage
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
    --no-cov -v

echo "Auth tests completed."
