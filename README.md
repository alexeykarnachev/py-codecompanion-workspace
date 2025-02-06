# cc-workspace

A CLI tool to generate workspace files for [CodeCompanion.nvim](https://github.com/olimorris/codecompanion.nvim) from YAML format.

## Key Features
- Converts YAML workspace configs to CodeCompanion-compatible JSON format
- Smart file pattern discovery with customizable ignore rules
- Multiple workspace templates (default and development)
- Built-in project conventions and documentation

## Quick Start

Install the package:
```bash
uv sync
```

Activate virtual environment (or use direct path to the `ccw` executable: `./.venv/bin/ccw`):
```bash
source .venv/bin/activate
```

Initialize a new workspace:
```bash
# Basic workspace
ccw init

# Development workspace with extended patterns
ccw init --template dev
```

This will create `./.cc/` directory with:
- `codecompanion.yaml` - workspace configuration in YAML format
- `data/` - project documentation and conventions
- `codecompanion-workspace.json` - compiled configuration

Modify the YAML config and apply changes:
```bash
ccw compile-config ./.cc/codecompanion.yaml
```

## Configuration

### Ignore Patterns

Control which files are included in your workspace:

```yaml
ignore:
  enabled: true
  # Use specific categories of ignore patterns
  categories:
    - dependencies  # node_modules, venv, __pycache__, etc.
    - ide          # .vscode, .idea, etc.
    - temp         # *.log, tmp/, etc.
    - packages     # *.egg-info, dist/, etc.
    - workspace    # .cc/, .git/, etc.
    - locks        # package lock files

  # Override patterns for specific categories
  patterns:
    locks:
      - custom.lock
      - special.lock

  # Add your own patterns
  additional:
    - "*.generated.*"
    - ".coverage.*"
```

### Templates

Available templates:
- `default` - Basic workspace with minimal configuration
- `dev` - Development workspace with comprehensive file patterns and documentation

## Development

Set up development environment:
```bash
./scripts/bootstrap.sh
```

This will:
1. Install dependencies
2. Initialize workspace
3. Run quality checks
4. Run tests

Set up pre-commit hooks:
```bash
pre-commit install
pre-commit install --hook-type pre-push
```

