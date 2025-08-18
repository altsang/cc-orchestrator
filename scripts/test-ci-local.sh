#!/bin/bash
# Local CI Testing Script
# Replicates the GitHub Actions CI environment locally to catch issues early

set -e

echo "🔍 Running local CI tests..."
echo "This script replicates the GitHub Actions CI pipeline locally"
echo

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Run this script from the project root directory"
    exit 1
fi

echo "📦 Installing dependencies..."
python -m pip install --upgrade pip
pip install -e ".[dev]"

echo
echo "🔍 Running linting checks..."
echo "Running ruff check..."
ruff check src/ tests/

echo
echo "🎨 Checking code formatting..."
echo "Running black check..."
black --check src/ tests/

echo
echo "🧪 Running tests with coverage..."
echo "Running pytest with exact CI configuration..."
# Use timeout to prevent hanging (same issue we just fixed)
timeout 300 pytest tests/ --cov=src --cov-report=xml --cov-fail-under=74 || {
    echo "❌ Tests failed or timed out after 5 minutes"
    echo "This indicates a hanging test or insufficient coverage"
    exit 1
}

echo
echo "✅ All CI checks passed locally!"
echo "🚀 Your changes should pass in the GitHub Actions CI pipeline"