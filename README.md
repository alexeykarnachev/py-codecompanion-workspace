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

The workspace configuration is stored in `.cc/codecompanion.yaml`. Here's an example:

```yaml
name: "my-project"
description: "Project description"
system_prompt: "Custom system prompt for LLM interactions"
ignore:
  enabled: true
  patterns:
    default: ["*.lock", ".env"]
  additional: ["custom.ignore"]
  categories: ["default"]
groups:
  - name: "Core"
    description: "Core project files"
    files:
      - path: "{package_name}/**/*.py"
        description: "Source files"
        kind: "pattern"
      - path: "tests/**/*.py"
        description: "Test files"
        kind: "pattern"
```

Key features:
- Pattern-based file discovery with `**/*` glob support
- Customizable ignore patterns
- File grouping for better organization
- Custom system prompts per group

After modifying the config:
1. Run `ccw compile-config .cc/codecompanion.yaml`
2. Use the generated `codecompanion-workspace.json` in Neovim

## License

[MIT](LICENSE)

