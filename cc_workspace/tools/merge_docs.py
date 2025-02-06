import asyncio
import re
from pathlib import Path

import aiofiles
import typer
from pydantic import BaseModel, Field
from rich.console import Console
from rich.prompt import Confirm

app = typer.Typer()
console = Console()

# Define arguments as module-level constants
SOURCE_ARG = typer.Argument(..., help="Source directory with markdown files")

OUTPUT_ARG = typer.Argument(..., help="Output file path")

INTERACTIVE_OPT = typer.Option(True, help="Enable interactive file selection")


class SourceFile(BaseModel):
    path: Path
    content: str | None = None
    level: int = Field(default=1, ge=1)


class ProcessingConfig(BaseModel):
    include_patterns: list[str] = ["*.md"]
    exclude_patterns: list[str] = ["node_modules/**", ".*", "assets/**"]
    adjust_headers: bool = True
    fix_links: bool = True


class CombinerConfig(BaseModel):
    source: Path
    output: Path
    config: ProcessingConfig = Field(default_factory=ProcessingConfig)


async def discover_files(config: CombinerConfig) -> list[SourceFile]:
    files: list[Path] = []
    for pattern in config.config.include_patterns:
        files.extend(config.source.glob(pattern))

    filtered_files = [
        f
        for f in files
        if not any(f.match(pat) for pat in config.config.exclude_patterns)
    ]

    return [SourceFile(path=f) for f in sorted(filtered_files)]


async def process_file(file: SourceFile, config: ProcessingConfig) -> str:
    async with aiofiles.open(file.path, encoding="utf-8") as f:
        content = await f.read()

    if config.adjust_headers:
        for i in range(6, 0, -1):
            pattern = f"^{'#' * i}"
            content = re.sub(
                pattern, "#" * (i + file.level - 1), content, flags=re.MULTILINE
            )

    if config.fix_links:
        content = re.sub(
            r"\[([^\]]+)\]\((?!http)([^)]+)\)",
            lambda m: f"[{m.group(1)}]({file.path.parent}/{m.group(2)})",
            content,
        )

    return content


async def write_output(path: Path, content: str) -> None:
    """Write content to the output file."""
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(content)


@app.command()
def merge(
    source: Path = SOURCE_ARG,
    output: Path = OUTPUT_ARG,
    interactive: bool = INTERACTIVE_OPT,
) -> None:
    """Merge markdown documents into a single file."""
    config = CombinerConfig(source=source, output=output)

    async def run() -> None:
        files = await discover_files(config)

        if not files:
            console.print("[red]No matching files found![/red]")
            raise typer.Exit(1)

        if interactive:
            console.print("\nFound files:")
            for f in files:
                console.print(f"  - {f.path.relative_to(source)}")

            if not Confirm.ask("\nProceed with these files?"):
                raise typer.Exit()

        contents: list[str] = []
        with console.status("Processing files..."):
            for file in files:
                content = await process_file(file, config.config)
                contents.append(content)

        merged_content = "\n\n".join(contents)
        await write_output(output, merged_content)

        console.print(
            f"[green]Successfully merged {len(files)} files to {output}[/green]"
        )

    asyncio.run(run())


if __name__ == "__main__":
    app()
