# cc-workspace

A CLI tool to generate workspace files for [CodeCompanion.nvim](https://github.com/olimorris/codecompanion.nvim) ✨

## Quick Start

### Initialize in Existing Project

```bash
cd my-project
uv add git+https://github.com/alexeykarnachev/py-codecompanion-workspace
ccw init .
```

### Create New Python Project

```bash
ccw init my-new-project
```

## What You Get

For any project:
- `.cc/codecompanion.yaml` - Workspace configuration
- `.cc/data/` - Project documentation
- `codecompanion-workspace.json` - Compiled configuration

For new Python projects:
- Basic project structure
- Tests directory with initial test
- Type hints and quality checks
- Version management

## Usage

### Basic Commands

```bash
# Initialize in current directory
ccw init .

# Create new project
ccw init my-project

# Force initialize in existing directory
ccw init my-project --force

# Use specific template
ccw init my-project --template default

# Update configuration after changes
ccw compile-config .cc/codecompanion.yaml
```

### Getting Help

```bash
ccw --help
ccw init --help
ccw compile-config --help
```

## Configuration

1. Edit `.cc/codecompanion.yaml` to configure your workspace
2. Run `ccw compile-config .cc/codecompanion.yaml` to update
3. Use the generated `codecompanion-workspace.json` in Neovim

## Development

```bash
# Install dev dependencies
uv add --dev git+https://github.com/alexeykarnachev/py-codecompanion-workspace

# Run tests
pytest

# Run quality checks
./scripts/quality.sh
```

## License

[MIT](LICENSE)

