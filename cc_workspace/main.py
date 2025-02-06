import fnmatch
import importlib.resources
import json
from pathlib import Path
from typing import Any, ClassVar, Literal

import typer
import yaml
from pydantic import BaseModel, Field
from rich.console import Console
from rich.progress import Progress, TextColumn

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


class File(BaseModel):
    description: str | None = None
    path: str
    kind: Literal["file", "pattern"] = "file"
    _ignore_patterns: set[str] | None = None

    model_config = {
        "arbitrary_types_allowed": True,
    }

    DEFAULT_IGNORE_PATTERNS: ClassVar[dict[str, set[str]]] = {
        "dependencies": {
            "node_modules/",
            "venv/",
            ".env/",
            "__pycache__/",
            "*.pyc",
            "target/",
            "dist/",
            "build/",
            ".tox/",
            ".pytest_cache/",
            ".coverage",
            "coverage/",
            ".hypothesis/",
        },
        "ide": {
            "*.swp",
            ".DS_Store",
            ".idea/",
            ".vscode/",
            "*.sublime-*",
            ".project",
            ".settings/",
            ".classpath",
            "*.iml",
        },
        "temp": {
            "*.log",
            "tmp/",
            "temp/",
            "*.tmp",
            "*.bak",
            "*.swp",
            "*~",
        },
        "packages": {
            "*.egg-info/",
            "*.egg",
            "*.whl",
            "*.tar.gz",
            "*.zip",
        },
        "workspace": {
            ".cc/",
            ".git/",
            ".hg/",
            ".svn/",
        },
        "locks": {
            "uv.lock",
            "poetry.lock",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "Cargo.lock",
            "Gemfile.lock",
            "composer.lock",
            "mix.lock",
            "go.sum",
            "requirements.txt.lock",
            "Pipfile.lock",
            "bun.lockb",
            "deno.lock",
            "flake.lock",
            "gradle.lockfile",
            "Podfile.lock",
            "pubspec.lock",
        },
    }

    @property
    def ignore_patterns(self) -> set[str]:
        """Get ignore patterns, using defaults if not set"""
        if self._ignore_patterns is None:
            return {
                pattern
                for patterns in self.DEFAULT_IGNORE_PATTERNS.values()
                for pattern in patterns
            }
        return self._ignore_patterns

    @ignore_patterns.setter
    def ignore_patterns(self, patterns: set[str]) -> None:
        self._ignore_patterns = patterns

    def should_ignore(self, path: str) -> bool:
        """Check if path matches any ignore pattern"""
        # Don't apply ignore patterns to explicitly listed files
        if self.kind == "file":
            return False

        # Normalize path
        path = str(path)
        if path.startswith("./"):
            path = path[2:]

        # Check for dot directories in path parts
        path_parts = Path(path).parts
        if any(part.startswith(".") for part in path_parts):
            return True

        # For patterns, check other ignore rules
        return any(
            fnmatch.fnmatch(path, pattern) if "*" in pattern else pattern in path
            for pattern in self.ignore_patterns
        )

    def resolve(self, base_path: Path) -> list["File"]:
        """Resolve pattern into actual files"""
        if self.kind == "pattern":
            resolved = []
            try:
                # Handle different glob patterns
                if "**" in self.path:
                    paths = base_path.rglob(self.path.replace("**/", ""))
                else:
                    paths = base_path.glob(self.path)

                # Process found paths
                for path in sorted(paths):
                    if not path.is_file():
                        continue

                    rel_path = str(path.relative_to(base_path))

                    # Skip empty files
                    if path.stat().st_size == 0:
                        continue

                    # Skip ignored paths
                    if self.should_ignore(rel_path):
                        continue

                    resolved.append(
                        File(
                            path=rel_path,
                            description=self.description,
                            kind="file",
                        )
                    )
            except Exception as e:
                print(f"Error resolving pattern {self.path}: {e}")
                return []

            return resolved
        else:
            # For explicit files, check if they should be ignored
            path = base_path / self.path
            if path.is_file() and path.stat().st_size > 0:
                rel_path = str(path.relative_to(base_path))
                if self.should_ignore(rel_path):
                    return []
                return [self]
            return []


class Group(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str = ""
    files: list[File] = Field(default_factory=list)
    symbols: list[File] = Field(default_factory=list)

    def resolve_patterns(self, base_path: Path) -> dict[str, Any]:
        """Resolve file patterns into actual files"""
        data = self.model_dump()

        # Resolve patterns to actual files
        resolved_files = []
        for file in self.files:
            resolved_files.extend(file.resolve(base_path))
        data["files"] = [
            {"path": f.path, "description": f.description} for f in resolved_files
        ]

        return data


class WorkspaceIgnore(BaseModel):
    enabled: bool = True
    patterns: dict[str, list[str]] = Field(default_factory=dict)
    additional: list[str] = Field(default_factory=list)
    categories: list[str] = Field(
        default_factory=lambda: list(File.DEFAULT_IGNORE_PATTERNS.keys())
    )


class Workspace(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str = ""
    groups: list[Group] = Field(default_factory=list)
    ignore: WorkspaceIgnore = Field(default_factory=WorkspaceIgnore)

    def get_ignore_patterns(self) -> set[str]:
        """Get combined ignore patterns based on config"""
        if not self.ignore.enabled:
            return set()

        patterns = set()

        # Add patterns from enabled categories
        for category in self.ignore.categories:
            if category in File.DEFAULT_IGNORE_PATTERNS:
                patterns.update(File.DEFAULT_IGNORE_PATTERNS[category])

        # Override with custom patterns
        for category, custom_patterns in self.ignore.patterns.items():
            if category in File.DEFAULT_IGNORE_PATTERNS:
                # Remove default patterns for this category
                patterns.difference_update(File.DEFAULT_IGNORE_PATTERNS[category])
                # Add custom patterns
                patterns.update(custom_patterns)

        # Add additional patterns
        patterns.update(self.ignore.additional)

        return patterns

    def resolve_patterns(self, base_path: Path) -> dict[str, Any]:
        """Resolve patterns in all groups"""
        data = self.model_dump()
        data["groups"] = [g.resolve_patterns(base_path) for g in self.groups]
        return data


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
        yaml.dump(workspace.resolve_patterns(base_path=path), f, sort_keys=False)

    return config_path, cc_dir


def validate_workspace_files(workspace: Workspace, base_path: Path) -> list[str]:
    """Validate all files in workspace exist"""
    errors = []

    for group in workspace.groups:
        for file in group.files:
            # Skip validation for glob patterns
            if any(char in file.path for char in "*?[]"):
                continue

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

    base_path = config_path.parent.parent

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,  # This will clear the progress display when done
    ) as progress:
        # Read and validate YAML
        progress.add_task("├─ Reading config...", total=None)
        with open(config_path) as f:
            config = yaml.safe_load(f)

        progress.add_task("├─ Validating schema...", total=None)
        workspace = Workspace(**config)

        # Validate files exist
        progress.add_task("├─ Checking files...", total=None)
        errors = validate_workspace_files(workspace, config_path.parent.parent)
        if errors:
            raise ValueError("\n".join(["Invalid workspace:", *errors]))

        # Write JSON with resolved patterns
        progress.add_task("└─ Writing output...", total=None)
        with open(output_path, "w") as f:
            data = workspace.resolve_patterns(base_path=base_path)
            f.write(json.dumps(data, indent=2))


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
        # Debug output - make it more concise
        if template:
            console.print(f"Using template: {template}")

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
