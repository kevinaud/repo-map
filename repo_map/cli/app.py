"""Core CLI app setup."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import structlog
import typer
from rich.console import Console

if TYPE_CHECKING:
  from structlog.typing import FilteringBoundLogger

from repo_map.clipboard import copy_to_clipboard
from repo_map.logging_config import configure_logging
from repo_map.mapper import generate_aider_repomap

# stderr console for logs/stats, stdout console for the actual map data
err_console = Console(stderr=True)
out_console = Console()


def normalize_patterns(patterns: list[str] | None) -> list[str] | None:
  """
  Normalize glob patterns from CLI input.

  - Splits comma-separated values into individual patterns
  - Adds `**/` prefix to patterns without path separators for recursive matching
  """
  if not patterns:
    return None

  result: list[str] = []
  for pattern in patterns:
    # Split comma-separated patterns
    for p in pattern.split(","):
      p = p.strip()
      if not p:
        continue
      # If it's a simple name (no path separator or glob), make it match recursively
      if "/" not in p and "*" not in p:
        # Match both as a directory and files within
        result.append(f"{p}/")
        result.append(f"{p}/**")
      else:
        result.append(p)
  return result if result else None


def get_logger() -> FilteringBoundLogger:
  """Configure logging and return a logger instance."""
  configure_logging()
  return structlog.get_logger()


app = typer.Typer(
  help="Repo Map: Intelligent repository skeleton generator for LLMs.",
  no_args_is_help=True,
)


@app.command()
def generate(
  path: Annotated[
    Path,
    typer.Argument(
      exists=True, file_okay=False, dir_okay=True, help="Root directory to map"
    ),
  ] = Path("."),
  # Filtering
  include: Annotated[
    list[str] | None, typer.Option("--include", "-i", help="Glob patterns to include.")
  ] = None,
  exclude: Annotated[
    list[str] | None, typer.Option("--exclude", "-e", help="Glob patterns to exclude.")
  ] = None,
  extensions: Annotated[
    list[str] | None, typer.Option("--ext", help="Specific file extensions.")
  ] = None,
  no_gitignore: Annotated[
    bool, typer.Option("--no-gitignore", help="Disable reading .gitignore files.")
  ] = False,
  # Constraints
  tokens: Annotated[
    int, typer.Option("--tokens", "-t", help="Maximum token budget.")
  ] = 20000,
  model: Annotated[
    str, typer.Option("--model", "-m", help="Aider model name to use for mapping.")
  ] = "gemini",
  # Output
  copy: Annotated[
    bool, typer.Option("--copy", "-c", help="Copy output to system clipboard.")
  ] = False,
  output_file: Annotated[
    Path | None, typer.Option("--output", "-o", help="Write output to a specific file.")
  ] = None,
  summary: Annotated[
    bool,
    typer.Option("--summary", "-s", help="Output only the file list summary."),
  ] = False,
  quiet: Annotated[
    bool, typer.Option("--quiet", "-q", help="Suppress status logs and summary.")
  ] = False,
):
  """
  Generate a concise skeleton of your repository structure.
  """
  log = get_logger()

  # We only log debug info to structlog if needed, but for CLI UX, we use rich stderr
  if not quiet:
    log.info("scanning_repo", path=str(path))

  try:
    # Normalize patterns to handle comma-separated values and add recursive matching
    normalized_include = normalize_patterns(include)
    normalized_exclude = normalize_patterns(exclude)

    result = generate_aider_repomap(
      root_dir=path,
      token_limit=tokens,
      include_patterns=normalized_include,
      exclude_patterns=normalized_exclude,
      allowed_extensions=extensions,
      use_gitignore=not no_gitignore,
      model_name=model,
    )

    if not result:
      if not quiet:
        err_console.print("[yellow]No matching files found.[/yellow]")
      return

    # --- Determine Output Content ---
    sorted_files = sorted(result.files)
    map_content = result.content
    output_content = "\n".join(sorted_files) if summary else map_content

    # --- Output Handling ---
    if copy:
      success = copy_to_clipboard(output_content)
      if success:
        if not quiet:
          chars = len(output_content)
          label = "summary" if summary else "map"
          err_console.print(
            f"[bold green]✓ Copied {label} to clipboard[/bold green] ({chars} chars)"
          )
      else:
        err_console.print("[red]✗ Clipboard copy failed. Printing to stdout:[/red]")
        out_console.print(output_content)

    elif output_file:
      output_file.write_text(output_content, encoding="utf-8")
      if not quiet:
        err_console.print(f"[bold green]✓ Saved to {output_file}[/bold green]")

    else:
      # Default: Print to stdout
      out_console.print(output_content)

    # --- Summary Statistics (only when not in summary mode and not quiet) ---
    if not quiet and not summary:
      err_console.print(f"\n[bold]Mapped {len(result.files)} files:[/bold]")

      # A simple list is more copy-pasteable than a rich Tree.
      for f in sorted_files:
        err_console.print(f" - {f}", style="dim")

      err_console.print(
        f"\n[dim]Total Token Budget: {tokens} | Approx Chars: {len(map_content)}[/dim]"
      )

  except Exception as e:
    log.error("generation_failed", error=str(e))
    err_console.print(f"[red]Fatal Error: {e}[/red]")
    raise typer.Exit(code=1) from e


if __name__ == "__main__":
  app()
