import importlib.resources
from pathlib import Path
from typing import Any

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


class FilePattern(BaseModel):
    pattern: str
    description: str | None = None


class Group(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str = ""
    files: list[FileRef | FilePattern] = Field(default_factory=list)
    resolved_files: list[FileRef] | None = Field(default=None, exclude=True)
    symbols: list[FileRef] = Field(default_factory=list)

    def get_files(self) -> list[FileRef]:
        """Get resolved files, resolving patterns if needed"""
        if self.resolved_files is None:
            raise ValueError("Files not resolved. Call resolve_patterns() first")
        return self.resolved_files

    def resolve_patterns(self, base_path: Path) -> None:
        """Resolve glob patterns to actual files"""
        resolved: list[FileRef] = []

        for spec in self.files:
            if isinstance(spec, FilePattern):
                # Handle glob pattern
                for path in sorted(base_path.glob(spec.pattern)):
                    if path.is_file():
                        desc = (
                            spec.description or f"{path.stem.replace('_', ' ').title()}"
                        )
                        resolved.append(
                            FileRef(
                                path=str(path.relative_to(base_path)), description=desc
                            )
                        )
            else:
                # Handle explicit FileRef
                resolved.append(spec)

        self.resolved_files = resolved


class Workspace(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str = ""
    groups: list[Group] = Field(default_factory=list)


class Template(BaseModel):
    name: str
    description: str
    content: str
    variables: dict[str, str] = Field(
        default_factory=lambda: {"project_name": "Project name"}
    )

    def render(self, **kwargs: Any) -> Workspace:
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
        content=importlib.resources.files("cc_workspace.data")
        .joinpath("CONVENTIONS.md")
        .read_text(),
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


def load_templates() -> TemplateLibrary:
    """Load all templates from data/templates directory"""
    templates = {}
    template_dir = importlib.resources.files("cc_workspace.data.templates")

    for template_path in template_dir.iterdir():
        if Path(str(template_path)).suffix == ".yaml":
            name = Path(str(template_path)).stem
            content = template_path.read_text()
            templates[name] = Template(
                name=name,
                description=f"{name.title()} template",
                content=content,
            )

    return TemplateLibrary(templates=templates)


TEMPLATES = load_templates()


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

    # First resolve all patterns
    for group in workspace.groups:
        group.resolve_patterns(base_path)

    # Then validate resolved files
    for group in workspace.groups:
        for file in group.get_files():
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
