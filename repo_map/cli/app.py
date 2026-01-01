"""Core CLI app setup."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import structlog
import typer
from pydantic import ValidationError
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

if TYPE_CHECKING:
  from structlog.typing import FilteringBoundLogger

from repo_map.clipboard import copy_to_clipboard
from repo_map.core.flight_plan import FlightPlan, format_validation_errors
from repo_map.logging_config import configure_adk_debug_logging, configure_logging
from repo_map.mapper import generate_repomap
from repo_map.settings import Settings

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
  # Configuration
  config: Annotated[
    Path | None,
    typer.Option("--config", "-C", help="Path to Flight Plan YAML configuration file."),
  ] = None,
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
    int | None, typer.Option("--tokens", "-t", help="Maximum token budget.")
  ] = None,
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
  # Cost prediction options
  show_costs: Annotated[
    bool,
    typer.Option(
      "--show-costs",
      help="Include cost annotations showing tokens at each verbosity level.",
    ),
  ] = False,
  strict: Annotated[
    bool,
    typer.Option(
      "--strict",
      help="Fail with error if output exceeds token budget.",
    ),
  ] = False,
):
  """
  Generate a concise skeleton of your repository structure.
  """
  log = get_logger()

  # --- Load Flight Plan if provided ---
  flight_plan: FlightPlan | None = None
  if config:
    try:
      flight_plan = FlightPlan.from_yaml_file(config)
      if not quiet:
        log.info("loaded_flight_plan", path=str(config))
    except FileNotFoundError:
      err_console.print(f"[red]Error: Flight plan not found: {config}[/red]")
      raise typer.Exit(code=3) from None
    except ValidationError as e:
      err_console.print(f"[red]{format_validation_errors(e.errors())}[/red]")
      raise typer.Exit(code=2) from None
    except ValueError as e:
      err_console.print(f"[red]Error: {e}[/red]")
      raise typer.Exit(code=2) from None

  # --- Determine effective token budget (CLI > FlightPlan > default) ---
  effective_tokens = tokens
  if effective_tokens is None:
    effective_tokens = flight_plan.budget if flight_plan is not None else 20000

  # We only log debug info to structlog if needed, but for CLI UX, we use rich stderr
  if not quiet:
    log.info("scanning_repo", path=str(path))

  try:
    # Normalize patterns to handle comma-separated values and add recursive matching
    normalized_include = normalize_patterns(include)
    normalized_exclude = normalize_patterns(exclude)

    result = generate_repomap(
      root_dir=path,
      token_limit=effective_tokens,
      include_patterns=normalized_include,
      exclude_patterns=normalized_exclude,
      allowed_extensions=extensions,
      use_gitignore=not no_gitignore,
      flight_plan=flight_plan,
      show_costs=show_costs,
      strict=strict,
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

      budget_info = f"Budget: {effective_tokens} | Chars: {len(map_content)}"
      err_console.print(f"\n[dim]{budget_info}[/dim]")

  except Exception as e:
    log.error("generation_failed", error=str(e))
    err_console.print(f"[red]Fatal Error: {e}[/red]")
    raise typer.Exit(code=1) from e


@app.command()
def navigate(
  path: Annotated[
    Path,
    typer.Argument(
      exists=True, file_okay=False, dir_okay=True, help="Root directory to explore"
    ),
  ] = Path("."),
  goal: Annotated[
    str,
    typer.Option(
      "--goal",
      "-g",
      help="Description of your task or what you're looking for.",
    ),
  ] = "",
  tokens: Annotated[
    int | None,
    typer.Option("--tokens", "-t", help="Maximum token budget for context window."),
  ] = None,
  cost_limit: Annotated[
    float | None,
    typer.Option("--cost-limit", help="Maximum USD to spend on exploration."),
  ] = None,
  model: Annotated[
    str | None,
    typer.Option("--model", "-m", help="LLM model to use for navigation."),
  ] = None,
  max_iterations: Annotated[
    int,
    typer.Option("--max-iterations", help="Maximum exploration iterations."),
  ] = 20,
  output_file: Annotated[
    Path | None,
    typer.Option("--output", "-o", help="Write context output to a file."),
  ] = None,
  flight_plan: Annotated[
    Path | None,
    typer.Option("--flight-plan", "-f", help="Export flight plan to YAML."),
  ] = None,
  copy: Annotated[
    bool,
    typer.Option("--copy", "-c", help="Copy context output to clipboard."),
  ] = False,
  quiet: Annotated[
    bool,
    typer.Option("--quiet", "-q", help="Suppress progress output."),
  ] = False,
  debug: Annotated[
    bool,
    typer.Option("--debug", "-d", help="Enable verbose debug output."),
  ] = False,
):
  """
  Autonomously explore a repository to discover relevant context for your task.

  The Navigator agent iteratively refines its view of the codebase, starting
  with a broad overview and progressively focusing on areas relevant to your
  goal. It produces an optimized context window within your token budget.

  Example:
      repo-map navigate . -g "understand the authentication flow"
  """
  log = get_logger()
  settings = Settings()

  # Configure ADK debug logging if requested
  debug_log_file = None
  if debug:
    debug_log_file = configure_adk_debug_logging()
    err_console.print(f"[dim]Debug logging enabled → {debug_log_file}[/dim]")

  # Validate goal
  if not goal:
    err_console.print("[red]Error: --goal is required for navigation[/red]")
    raise typer.Exit(code=2)

  # Resolve settings with CLI overrides
  effective_tokens = tokens or settings.navigator_default_token_budget
  effective_cost_limit = cost_limit or settings.navigator_default_cost_limit_usd
  effective_model = model or settings.navigator_model

  # Run the async navigation
  try:
    result = asyncio.run(
      _run_navigation(
        path=path,
        goal=goal,
        tokens=effective_tokens,
        cost_limit=effective_cost_limit,
        model=effective_model,
        max_iterations=max_iterations,
        quiet=quiet,
        debug=debug,
        log=log,
      )
    )
  except Exception as e:
    log.error("navigation_failed", error=str(e))
    err_console.print(f"[red]Navigation failed: {e}[/red]")
    raise typer.Exit(code=1) from e

  if result is None:
    err_console.print("[yellow]Navigation produced no results.[/yellow]")
    raise typer.Exit(code=1)

  # Handle output
  context_output = result.context_string

  if copy:
    success = copy_to_clipboard(context_output)
    if success:
      if not quiet:
        err_console.print(
          f"[bold green]✓ Copied context to clipboard[/bold green] "
          f"({len(context_output)} chars, ~{result.token_count} tokens)"
        )
    else:
      err_console.print("[red]✗ Clipboard copy failed. Printing to stdout:[/red]")
      out_console.print(context_output)
  elif output_file:
    output_file.write_text(context_output, encoding="utf-8")
    if not quiet:
      err_console.print(f"[bold green]✓ Saved context to {output_file}[/bold green]")
  else:
    out_console.print(context_output)

  # Export flight plan if requested
  if flight_plan:
    flight_plan.write_text(result.flight_plan_yaml, encoding="utf-8")
    if not quiet:
      err_console.print(f"[bold green]✓ Saved flight plan: {flight_plan}[/bold green]")

  # Print summary unless quiet
  if not quiet:
    err_console.print("\n[bold]Navigation Summary:[/bold]")
    err_console.print(f"  Iterations: {result.total_iterations}")
    err_console.print(f"  Total cost: ${result.total_cost:.4f}")
    err_console.print(f"  Token count: ~{result.token_count}")
    if result.reasoning_summary:
      err_console.print(f"\n[dim]{result.reasoning_summary}[/dim]")
    if debug_log_file:
      err_console.print(f"\n[dim]Full ADK debug logs: {debug_log_file}[/dim]")


async def _run_navigation(
  path: Path,
  goal: str,
  tokens: int,
  cost_limit: float,
  model: str,
  max_iterations: int,
  quiet: bool,
  debug: bool,
  log: FilteringBoundLogger,
):
  """Run the Navigator agent asynchronously."""
  from repo_map.navigator.runner import (
    NavigatorOutput,
    NavigatorProgress,
    create_navigator_runner,
    initialize_session,
    run_autonomous,
  )

  # Generate session identifiers
  user_id = "cli-user"
  session_id = str(uuid.uuid4())

  log.info(
    "starting_navigation",
    path=str(path),
    goal=goal[:50],
    tokens=tokens,
    cost_limit=cost_limit,
    model=model,
    max_iterations=max_iterations,
  )

  # Create runner
  runner, budget_plugin = create_navigator_runner(model=model)

  # Initialize session
  await initialize_session(
    runner=runner,
    user_id=user_id,
    session_id=session_id,
    repo_path=path,
    user_task=goal,
    token_budget=tokens,
    cost_limit=cost_limit,
    model=model,
  )

  result: NavigatorOutput | None = None

  if quiet:
    # Run without progress display
    async for item in run_autonomous(
      runner,
      budget_plugin,
      user_id,
      session_id,
      max_iterations=max_iterations,
      debug=debug,
    ):
      if isinstance(item, NavigatorOutput):
        result = item
  else:
    # Run with progress display
    with Progress(
      SpinnerColumn(),
      TextColumn("[progress.description]{task.description}"),
      console=err_console,
      transient=not debug,  # Keep output visible in debug mode
    ) as progress:
      task = progress.add_task("Exploring repository...", total=None)

      async for item in run_autonomous(
        runner,
        budget_plugin,
        user_id,
        session_id,
        max_iterations=max_iterations,
        debug=debug,
      ):
        if isinstance(item, NavigatorProgress):
          if debug:
            # In debug mode, print detailed progress
            err_console.print(
              f"[cyan]Step {item.step}[/cyan]: {item.action} | "
              f"tokens={item.tokens} | cost=${item.cost_so_far:.4f}"
            )
            err_console.print(f"  [dim]{item.message}[/dim]")
          else:
            progress.update(
              task,
              description=f"Step {item.step}: {item.action} (${item.cost_so_far:.4f})",
            )
        else:
          # NavigatorOutput - final result
          result = item

  return result


if __name__ == "__main__":
  app()
