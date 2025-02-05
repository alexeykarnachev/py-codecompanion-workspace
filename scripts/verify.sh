#!/bin/bash
set -e

echo "🔍 Running full verification..."

echo "├─ Running quality checks..."
bash scripts/quality.sh

echo "└─ Running tests..."
pytest -v tests/

echo "✨ All checks passed!"
