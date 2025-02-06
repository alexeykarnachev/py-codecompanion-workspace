import asyncio
import re
from pathlib import Path
from typing import List, Optional

import aiofiles
import typer
from pydantic import BaseModel, Field
from rich import print
from rich.console import Console
from rich.prompt import Confirm


class SourceFile(BaseModel):
    path: Path
    content: Optional[str] = None
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


console = Console()
app = typer.Typer()


async def discover_files(config: CombinerConfig) -> List[SourceFile]:
    files = []
    for pattern in config.config.include_patterns:
        files.extend(config.source.glob(pattern))

    filtered_files = [
        f
        for f in files
        if not any(f.match(pat) for pat in config.config.exclude_patterns)
    ]

    return [SourceFile(path=f) for f in sorted(filtered_files)]


async def process_file(file: SourceFile, config: ProcessingConfig) -> str:
    async with aiofiles.open(file.path, "r", encoding="utf-8") as f:
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


@app.command()
def merge(
    source: Path = typer.Argument(..., help="Source directory with markdown files"),
    output: Path = typer.Argument(..., help="Output file path"),
    interactive: bool = typer.Option(True, help="Enable interactive file selection"),
) -> None:
    """Merge markdown documents into a single file."""
    config = CombinerConfig(source=source, output=output)

    async def run():
        files = await discover_files(config)

        if not files:
            console.print("[red]No matching files found![/red]")
            raise typer.Exit(1)

        if interactive:
            print("\nFound files:")
            for f in files:
                print(f"  - {f.path.relative_to(source)}")

            if not Confirm.ask("\nProceed with these files?"):
                raise typer.Exit()

        contents = []
        with console.status("Processing files..."):
            for file in files:
                content = await process_file(file, config.config)
                contents.append(content)

        async with aiofiles.open(output, "w", encoding="utf-8") as f:
            await f.write("\n\n".join(contents))

        console.print(
            f"[green]Successfully merged {len(files)} files to {output}[/green]"
        )

    asyncio.run(run())


if __name__ == "__main__":
    app()
