# cc-workspace

A CLI tool to generate workspace files for [CodeCompanion.nvim](https://github.com/olimorris/codecompanion.nvim) from YAML format ✨

## Quick Start

Install and initialize workspace:

```bash
# Install from git
uv add git+https://github.com/alexeykarnachev/py-codecompanion-workspace

# Basic workspace
ccw init

# Development workspace
ccw init --template dev
```

This creates:
- `.cc/codecompanion.yaml` - workspace configuration
- `.cc/data/` - project documentation
- `codecompanion-workspace.json` - compiled configuration

Update configuration:
```bash
ccw compile-config .cc/codecompanion.yaml
```

