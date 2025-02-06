# cc-workspace

A CLI tool to generate workspace files for [CodeCompanion.nvim](https://github.com/olimorris/codecompanion.nvim) from YAML format.

## Key Features
- Converts YAML workspace configs to CodeCompanion-compatible JSON format
- Smart file pattern discovery with default ignore rules
- Multiple workspace templates (default and development)
- Project conventions and documentation included

## Quick Start

Install the package:
```bash
uv sync
```

Initialize a new workspace:
```bash
# Basic workspace
ccw init

# Development workspace
ccw init --template dev
```

This will create `./.cc/` directory with:
- `codecompanion.yaml` - workspace configuration in YAML format
- `data/` - project documentation and conventions
- `codecompanion-workspace.json` - compiled configuration in project root

Modify the YAML config and recompile:
```bash
ccw compile-config ./.cc/codecompanion.yaml
```

## Configuration

### Ignore Patterns

Control which files are included in your workspace:

```yaml
ignore:
  enabled: true  # Set to false to include all files
  additional:    # Add your own patterns to ignore
    - "*.generated.*"
    - ".coverage.*"
```

By default, the tool ignores:
- Dependencies (node_modules, venv, __pycache__, etc.)
- IDE files (.vscode, .idea, etc.)
- Temporary files (*.log, tmp/, etc.)
- Package artifacts (*.egg-info, dist/, etc.)
- Workspace files (.cc/, .git/, etc.)
- Lock files (package-lock.json, etc.)
- Empty files and symlinks

### Templates

Available templates:
- `default` - Basic workspace with minimal configuration
- `dev` - Development workspace with extended patterns and documentation

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

