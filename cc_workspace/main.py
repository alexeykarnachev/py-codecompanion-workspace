import importlib.resources
from pathlib import Path
from typing import Any, Self

import typer
import yaml
from pydantic import BaseModel, Field
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer()
console = Console()

# CLI Arguments
INIT_PATH_ARG = typer.Argument(
    default=Path("."),
    help="Project path",
    exists=True,
    dir_okay=True,
    file_okay=False,
)

COMPILE_CONFIG_ARG = typer.Argument(
    ...,
    help="Path to YAML config",
    exists=True,
    dir_okay=False,
    file_okay=True,
)

COMPILE_OUTPUT_OPT = typer.Option(
    None,
    help="Output JSON path",
    dir_okay=False,
    file_okay=True,
)


# Base Models
class FileRef(BaseModel):
    description: str | None = None
    path: str


class Group(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str | None = None
    files: list[FileRef] = Field(default_factory=list)
    symbols: list[FileRef] = Field(default_factory=list)


class Workspace(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str | None = None
    groups: list[Group] = Field(default_factory=list)


# Template Models
class Template(BaseModel):
    name: str
    description: str
    content: str
    variables: dict[str, str] = Field(
        default_factory=lambda: {"project_name": "Project name"}
    )

    def render(self: Self, **kwargs: Any) -> Workspace:
        """Render template with variables and return validated Workspace"""
        content = self.content.format(**kwargs)
        config = yaml.safe_load(content)
        return Workspace(**config)


class TemplateLibrary(BaseModel):
    templates: dict[str, Template] = Field(default_factory=dict)

    def get(self, name: str) -> Template | None:
        return self.templates.get(name)

    def list_templates(self) -> list[str]:
        return list(self.templates.keys())


class FileContent(BaseModel):
    description: str | None = None
    path: str
    content: str


class DataFiles:
    CONVENTIONS = FileContent(
        path="CONVENTIONS.md",
        description="Project conventions and guidelines",
        content="""
# Project Conventions

## Task Approach
- Stay focused on the immediate task
- Minimize scope creep and over-engineering
- For small tasks (1-20 LOC):
  - Implement directly when requirements are clear
  - Provide solution in a single response
- For larger tasks:
  - First discuss the approach
  - Request necessary documentation/files
  - Break down into smaller steps
  - Proceed only after approval
- Additional improvements can be suggested separately after task completion

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

""".strip(),
    )
    CODECOMPANION_DOC = FileContent(
        path="codecompanion_doc.md",
        description="CodeCompanion documentation",
        content=importlib.resources.files("cc_workspace.data")
        .joinpath("codecompanion_doc.md")
        .read_text(),
    )


def ensure_cc_structure(path: Path) -> tuple[Path, Path]:
    """Create .cc directory structure"""
    cc_dir = path / ".cc"
    data_dir = cc_dir / "data"

    cc_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    # Create default files
    for file in [DataFiles.CONVENTIONS, DataFiles.CODECOMPANION_DOC]:
        file_path = data_dir / file.path
        if not file_path.exists():
            with open(file_path, "w") as f:
                f.write(file.content)

    return cc_dir, data_dir


TEMPLATES = TemplateLibrary(
    templates={
        "default": Template(
            name="default",
            description="Basic template for any project",
            content="""
name: "{project_name}"
description: "CodeCompanion workspace for {project_name}"
groups:
  - name: "Main"
    description: "Project files"
    files:
      - path: ".cc/data/CONVENTIONS.md"
        description: "Project conventions and guidelines"
""",
        ),
    }
)


def ensure_cc_dir(path: Path) -> Path:
    """Ensure .cc directory exists and return its path"""
    cc_dir = path / ".cc"
    cc_dir.mkdir(exist_ok=True)
    return cc_dir


def create_workspace(path: Path, template_name: str | None = None) -> tuple[Path, Path]:
    """Create a new workspace and return paths to yaml config and cc dir"""
    cc_dir, _ = ensure_cc_structure(path)
    config_path = cc_dir / "codecompanion.yaml"
    project_name = path.absolute().name

    # Get and validate template
    template = TEMPLATES.get(template_name or "default")
    if not template:
        available = TEMPLATES.list_templates()
        raise ValueError(
            f"Template '{template_name}' not found. Available: {available}"
        )

    # Render template and validate
    workspace = template.render(project_name=project_name)

    # Write to file
    with open(config_path, "w") as f:
        yaml.dump(workspace.model_dump(), f, sort_keys=False)

    return config_path, cc_dir


def validate_workspace_files(workspace: Workspace, base_path: Path) -> list[str]:
    """Validate all files in workspace exist"""
    errors = []

    for group in workspace.groups:
        for file in group.files:
            path = base_path / file.path
            if not path.exists():
                errors.append(f"File not found: {file.path}")

        for symbol in group.symbols:
            path = base_path / symbol.path
            if not path.exists():
                errors.append(f"Symbol file not found: {symbol.path}")

    return errors


def compile_workspace(config_path: Path, output_path: Path | None = None) -> None:
    """Compile YAML to JSON"""
    if not output_path:
        output_path = config_path.parent.parent / "codecompanion-workspace.json"

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Read and validate YAML
        progress.add_task("Reading config...", total=None)
        with open(config_path) as f:
            config = yaml.safe_load(f)

        progress.add_task("Validating schema...", total=None)
        workspace = Workspace(**config)

        # Validate files exist
        progress.add_task("Checking files...", total=None)
        errors = validate_workspace_files(workspace, config_path.parent.parent)
        if errors:
            raise ValueError("\n".join(["Invalid workspace:", *errors]))

        # Write JSON
        progress.add_task("Writing output...", total=None)
        with open(output_path, "w") as f:
            f.write(workspace.model_dump_json(indent=2))


@app.command()
def init(
    path: Path = INIT_PATH_ARG,
    template: str = typer.Option(
        None,
        help=f"Template to use: {', '.join(TEMPLATES.list_templates())}",
    ),
    skip_compile: bool = typer.Option(
        False,
        help="Skip compiling to JSON after initialization",
    ),
) -> None:
    """Initialize a new CodeCompanion workspace"""
    try:
        config_path, cc_dir = create_workspace(path, template)
        console.print(f"✨ Initialized workspace at {path}")
        console.print(f"📁 CCW files stored in {cc_dir}")

        if not skip_compile:
            compile_workspace(config_path)
            console.print("✨ Compiled workspace config")
    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")
        raise typer.Exit(1) from e


@app.command()
def compile_config(
    config: Path = COMPILE_CONFIG_ARG,
    output: Path | None = COMPILE_OUTPUT_OPT,
) -> None:
    """Compile YAML config to CodeCompanion workspace JSON"""
    try:
        compile_workspace(config, output)
        console.print("✨ Compiled workspace config")
    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()


# TODO: [see below]

# 1. Tests:
# - Add test for `uv` package management in `setup_dev_workspace.sh`
# - Test workspace file validation (invalid YAML structure, missing required fields)
# - Test template variables substitution

# 2. Features:
# - Add workspace validation command (`ccw validate`)
# - Add template list command (`ccw templates list`)
# - Add template creation command (`ccw templates new`)
# - Support URLs in workspace files (like CodeCompanion.nvim does)

# 3. Code improvements:
# - Move templates to separate YAML files
# - Add proper error messages for workspace validation
# - Add workspace schema version validation

# The most important next step is workspace validation
# since it will help catch configuration errors early.
