# cc-workspace

A CLI tool to generate workspace files for [CodeCompanion.nvim](https://github.com/olimorris/codecompanion.nvim) from YAML format ✨

## Quick Start

Install and initialize workspace; in your project's root run:

```bash
uv add git+https://github.com/alexeykarnachev/py-codecompanion-workspace
ccw init
```

This creates:
- `.cc/codecompanion.yaml` - workspace configuration
- `.cc/data/` - project documentation
- `codecompanion-workspace.json` - compiled configuration

Update configuration:
```bash
ccw compile-config .cc/codecompanion.yaml
```

