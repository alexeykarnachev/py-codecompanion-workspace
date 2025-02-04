# cc-workspace

A CLI tool to generate workspace files for [CodeCompanion.nvim](https://github.com/olimorris/codecompanion.nvim) from YAML format.

## Key Feature
Converts YAML workspace configs to CodeCompanion-compatible JSON format.

## Quick Start

Install the package:
```bash
uv sync
```

Activate virtual environment (or use direct path to the `ccw` executable: `./.venv/bin/ccw`):
```bash
source .venv/bin/activate
```

Then, in your project run the tool
```bash
ccw init
ccw compile-config <yaml-path>
```

This will create `./.cc/` directory with a yaml format of codecompanion documentation. You can modify it and apply changes:

```bash
ccw compile-config ./.cc/codecompanion.yaml
```

## Development
Set up pre-commit hooks:
```bash
pre-commit install
pre-commit install --hook-type pre-push
```
