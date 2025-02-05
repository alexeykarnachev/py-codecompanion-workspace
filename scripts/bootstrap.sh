#!/bin/bash
set -e

echo "🧹 Cleaning up existing workspace files..."
rm -rf .cc codecompanion-workspace.json

echo "📦 Installing package..."
uv add --dev .
uv add pytest pytest-cov ruff mypy types-pyyaml

echo "🚀 Initializing workspace..."
python -m cc_workspace init .

echo "📝 Copying CodeCompanion documentation... (can be attached manually in codecompanion nvim session via `/file` command)"
mkdir -p .cc/data
cp cc_workspace/data/codecompanion_doc.md .cc/data/codecompanion_doc.md || true

echo "🧪 Running workspace tests..."
pytest -v tests/test_integration.py -k test_dev_workspace_structure

echo "✨ Dev workspace setup complete!"
