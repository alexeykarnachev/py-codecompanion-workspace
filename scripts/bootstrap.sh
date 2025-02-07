#!/bin/bash
set -e

echo "🧹 Cleaning up existing workspace files..."
rm -rf .cc codecompanion-workspace.json

echo "📦 Installing package..."
echo "├─ Installing development dependencies..."
uv add --dev .
echo "└─ Installing test dependencies..."
uv add pytest pytest-cov ruff mypy types-pyyaml

echo "🚀 Initializing workspace..."
echo "├─ Creating workspace structure..."
python -m cc_workspace init . --force

echo "🔍 Running verification..."
echo "├─ Quality checks"
./scripts/quality.sh | sed 's/🔍 Running code quality checks...//g' # Remove duplicate header
echo "└─ Integration tests"
pytest -v tests/test_integration.py

echo
echo "✨ Dev workspace setup complete!"
echo
echo "Next steps:"
echo "1. Review .cc/codecompanion.yaml for workspace configuration"
echo "2. Run 'ccw compile-config .cc/codecompanion.yaml' to update workspace"
echo "3. Check codecompanion-workspace.json for the compiled configuration"

