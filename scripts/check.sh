#!/bin/bash
set -e

echo "🛠️ Setting up dev workspace..."
bash scripts/setup_dev_workspace.sh

echo "🧹 Running isort..."
isort cc_workspace/ tests/ scripts/ --check --diff

echo "🔍 Running ruff..."
ruff check cc_workspace/ tests/ scripts/ --select F,E,W,I,N,UP,B,A,C4,SIM,ERA,PL,RUF,F401,F403,F405,F821,F822,F823,F841

echo "🔎 Running mypy..."
mypy --strict --ignore-missing-imports cc_workspace/ tests/ scripts/

echo "🧪 Running tests..."
pytest -v tests/

echo "✨ All checks passed!"
