# cc-workspace

A CLI tool to generate workspace files for [CodeCompanion.nvim](https://github.com/olimorris/codecompanion.nvim) from YAML format ✨

## Installation

Install globally:
```bash
uv pip install --system cc-workspace
```

## Quick Start

Initialize workspace:
```bash
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

## Configuration

### File Discovery

Control which files to include:

```yaml
ignore:
  enabled: true  # Set to false to include all files
  additional:    # Add custom patterns
    - "*.generated.*"
    - ".coverage"

