#!/bin/bash
set -e

echo "🧹 Cleaning up existing workspace files..."
rm -rf .cc codecompanion-workspace.json

echo "📦 Installing package..."
uv add --dev .
uv add pytest pytest-cov ruff mypy types-pyyaml

echo "🚀 Initializing workspace..."
python -m cc_workspace init . --template _ccw_dev

echo "🔍 Running quality checks..."
./scripts/quality.sh

echo "🧪 Running workspace tests..."
pytest -v tests/test_integration.py

echo "✨ Dev workspace setup complete!"
