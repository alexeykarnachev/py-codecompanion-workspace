#!/bin/bash
set -e

echo "🔍 Running code quality checks..."

echo "├─ Running isort..."
isort cc_workspace/ tests/ scripts/ --check --diff

echo "├─ Running ruff..."
ruff check cc_workspace/ tests/ scripts/ --select F,E,W,I,N,UP,B,A,C4,SIM,ERA,PL,RUF,F841

echo "└─ Running mypy..."
mypy --strict --ignore-missing-imports cc_workspace/ tests/ scripts/

echo "✨ All quality checks passed!"
