from pathlib import Path
from typing import Any, Dict, List, Optional, Self, Tuple

import typer
import yaml
from pydantic import BaseModel, Field
from rich.console import Console

app = typer.Typer()
console = Console()


# Base Models
class FileRef(BaseModel):
    description: Optional[str] = None
    path: str


class Group(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    files: List[FileRef] = Field(default_factory=list)
    symbols: List[FileRef] = Field(default_factory=list)


class Workspace(BaseModel):
    name: str
    version: str = "0.1.0"
    workspace_spec: str = "1.0"
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    groups: List[Group] = Field(default_factory=list)


# Template Models
class Template(BaseModel):
    name: str
    description: str
    content: str
    variables: Dict[str, str] = Field(
        default_factory=lambda _: dict[str, str]({"project_name": "Project name"})
    )

    def render(self: Self, **kwargs: Any) -> Workspace:
        """Render template with variables and return validated Workspace"""
        content = self.content.format(**kwargs)
        config = yaml.safe_load(content)
        return Workspace(**config)


class TemplateLibrary(BaseModel):
    templates: Dict[str, Template] = Field(default_factory=dict)

    def get(self, name: str) -> Optional[Template]:
        return self.templates.get(name)

    def list_templates(self) -> List[str]:
        return list(self.templates.keys())


class FileContent(BaseModel):
    description: Optional[str] = None
    path: str
    content: str


class DataFiles:
    CONVENTIONS = FileContent(
        path="CONVENTIONS.md",
        description="Project conventions and guidelines",
        content="""# Project Conventions

## Overview
This document outlines the key conventions and guidelines for this project.

## Structure
- `.cc/` - CodeCompanion workspace files
  - `data/` - Additional documentation and resources
  - `codecompanion.yaml` - Workspace configuration
- `codecompanion-workspace.json` - Compiled workspace configuration

## Guidelines
1. Keep documentation up to date
2. Follow the project's coding standards
3. Update this file as conventions evolve
""",
    )


def ensure_cc_structure(path: Path) -> Tuple[Path, Path]:
    """Create .cc directory structure"""
    cc_dir = path / ".cc"
    data_dir = cc_dir / "data"

    cc_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    # Create default files
    conventions_path = data_dir / DataFiles.CONVENTIONS.path
    if not conventions_path.exists():
        with open(conventions_path, 'w') as f:
            f.write(DataFiles.CONVENTIONS.content)

    return cc_dir, data_dir


TEMPLATES = TemplateLibrary(
    templates={
        "default": Template(
            name="default",
            description="Feature-complete minimal template",
            content="""
name: "{project_name}"
version: "0.1.0"
workspace_spec: "1.0"
description: "CodeCompanion workspace demonstrating key features"
system_prompt: '''
You are a development assistant for the {project_name} project.
Please follow the conventions in .cc/data/CONVENTIONS.md.
'''
groups:
  - name: "Documentation"
    description: "Project documentation and conventions"
    files:
      - path: ".cc/data/CONVENTIONS.md"
        description: "Project conventions and guidelines"
      - path: "README.md"
        description: "Project overview and setup instructions"

  - name: "Source"
    description: "Main source code"
    files: []
    symbols: []

  - name: "Tests"
    description: "Test suite"
    files: []
    symbols: []
""",
        )
    }
)


def ensure_cc_dir(path: Path) -> Path:
    """Ensure .cc directory exists and return its path"""
    cc_dir = path / ".cc"
    cc_dir.mkdir(exist_ok=True)
    return cc_dir


def create_workspace(
    path: Path, template_name: Optional[str] = None
) -> Tuple[Path, Path]:
    """Create a new workspace and return paths to yaml config and cc dir"""
    cc_dir, data_dir = ensure_cc_structure(path)
    config_path = cc_dir / "codecompanion.yaml"
    project_name = path.absolute().name

    # Get and validate template
    template = TEMPLATES.get(template_name or "default")
    if not template:
        raise ValueError(
            f"Template '{template_name}' not found. Available templates: {', '.join(TEMPLATES.list_templates())}"
        )

    # Render template and validate
    workspace = template.render(project_name=project_name)

    # Write to file
    with open(config_path, "w") as f:
        yaml.dump(workspace.model_dump(), f, sort_keys=False)

    return config_path, cc_dir


def compile_workspace(config_path: Path, output_path: Optional[Path] = None) -> None:
    """Compile YAML to JSON"""
    if not output_path:
        output_path = config_path.parent.parent / "codecompanion-workspace.json"

    # Read and validate YAML
    with open(config_path) as f:
        config = yaml.safe_load(f)
    workspace = Workspace(**config)

    # Write JSON
    with open(output_path, "w") as f:
        f.write(workspace.model_dump_json(indent=2))


@app.command()
def init(
    path: Path = typer.Argument(
        default=Path("."),
        help="Project path",
        exists=True,
        dir_okay=True,
        file_okay=False,
    ),
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
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def compile(
    config: Path = typer.Argument(
        ...,
        help="Path to YAML config",
        exists=True,
        dir_okay=False,
        file_okay=True,
    ),
    output: Optional[Path] = typer.Option(
        None,
        help="Output JSON path",
        dir_okay=False,
        file_okay=True,
    ),
) -> None:
    """Compile YAML config to CodeCompanion workspace JSON"""
    try:
        compile_workspace(config, output)
        console.print("✨ Compiled workspace config")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
