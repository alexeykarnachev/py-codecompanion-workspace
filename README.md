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
- `.cc/data/` - Internal cc files (e.g `CONVENTIONS.md`)
- `codecompanion-workspace.json` - Compiled configuration

For new Python projects:
- Basic Python project structure:
  - Package directory with `__init__.py` and `main.py`
  - Tests directory with initial test
  - Scripts directory with quality checks
- Configuration files:
  - `pyproject.toml` with modern tools setup
  - Type hints and quality checks configuration
  - Version management
- Documentation:
  - README.md with quick start guide
  - CHANGELOG.md following Keep a Changelog format
  - .gitignore with comprehensive Python patterns
- Git repository:
  - Initialized with initial commit
  - Using your Git configuration

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

## License

[MIT](LICENSE)
