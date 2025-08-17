#!/bin/bash

# Script to run auth tests without coverage requirements

echo "Running authentication tests without coverage requirements..."

# Set working directory to project root
cd "$(dirname "$0")/.."

# Define the failing auth tests
AUTH_TESTS=(
    "tests/unit/test_web_auth.py::TestTokenFunctions::test_create_access_token_default_expiry"
    "tests/unit/test_web_auth.py::TestTokenFunctions::test_create_access_token_custom_expiry"
    "tests/unit/test_web_auth.py::TestGetCurrentUser::test_get_current_user_no_exp_claim"
    "tests/unit/test_web_auth.py::TestModuleConstants::test_secret_key_from_environment"
    "tests/unit/test_web_auth_coverage.py::TestTokenOperations::test_create_access_token_default_expiry"
    "tests/unit/test_web_auth_coverage.py::TestTokenOperations::test_create_access_token_custom_expiry"
    "tests/unit/test_web_auth_coverage.py::TestTokenOperations::test_create_access_token_no_expiry_delta"
    "tests/unit/test_web_auth_coverage.py::TestGetCurrentUser::test_get_current_user_expired_token"
    "tests/unit/test_web_auth_coverage.py::TestGetCurrentUser::test_get_current_user_no_exp_claim"
)

# Run the specific failing auth tests without coverage using custom config
python -m pytest \
    -c pytest-auth.ini \
    -xvs \
    "${AUTH_TESTS[@]}"

exit_code=$?
echo "Auth tests completed with exit code: $exit_code"

if [ $exit_code -eq 0 ]; then
    echo "✅ All 9 authentication tests passed successfully!"
else
    echo "❌ Some authentication tests failed."
fi

exit $exit_code
