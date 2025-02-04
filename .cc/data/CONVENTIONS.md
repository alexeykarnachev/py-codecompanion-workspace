# Project Conventions

## Code Style
- Use Python 3.13+ with strict type hints
- Keep functions focused and minimal
- Use descriptive names
- Include language identifiers in code blocks
- Only show relevant code sections (if not asked otherwise)

## Package Management
- Use `uv` for all package operations
- Add runtime deps: `uv add <package>`
- Add dev deps: `uv add --dev <package>`
- Don't use pip or "uv pip" directly
- Your own workspace is in ./.cc/ directory

## Response Format
- Use Markdown with language identifiers in code blocks
- Keep responses concise
- Write brief step-by-step plans when needed

## Code Architecture
- Prefer data-centric design over heavy OOP
- Use Pydantic for strict data validation
- Keep business logic procedural and concentrated
- Minimize abstractions and inheritance
- Design clever, precise functions over complex class hierarchies

## Technology Stack
- Use modern, type-safe packages:
  - Litestar for APIs (preferred over FastAPI)
  - Pydantic for data validation
  - Pydantic-settings for configuration
  - Typer for CLIs
  - Rich/Textual for advanced TUI
  - Prompt-toolkit for simple CLI interactions or advanced keybindings (vim, emacs)
- Choose packages thoughtfully based on actual needs
- When introducing new package, provide `uv add` command for user
