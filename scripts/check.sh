#!/bin/bash
set -e

echo "🧹 Running isort..."
isort . --check --diff

echo "🔍 Running ruff..."
ruff check .

echo "🔎 Running mypy..."
mypy --strict --ignore-missing-imports .

echo "🧪 Running tests..."
pytest -v tests/

echo "✨ All checks passed!"
