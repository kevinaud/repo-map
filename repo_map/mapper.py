from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pathspec
from pydantic import BaseModel, Field

from repo_map.core import RepoMap

if TYPE_CHECKING:
  from pathlib import Path

  from repo_map.core.flight_plan import FlightPlan

# Opinionated defaults: Text files that are too noisy for an LLM map
DEFAULT_EXCLUDE_PATTERNS = [
  "uv.lock",
  "poetry.lock",
  "Pipfile.lock",
  "package-lock.json",
  "yarn.lock",
  "pnpm-lock.yaml",
  "go.sum",
  "Cargo.lock",
  "Gemfile.lock",
  ".editorconfig",
  ".prettierrc*",
  ".eslintrc*",
  ".ruff.toml",
  ".pylintrc",
  ".vscode/",
  ".idea/",
  ".gitattributes",
  ".gitmodules",
  "__pycache__/",
  "coverage.xml",
  ".DS_Store",
]


class MapResult(BaseModel):
  """Result from repo-map generation with content and metadata."""

  content: str = Field(description="Rendered repository map content")
  files: list[str] = Field(description="List of files included in the map")
  total_tokens: int = Field(default=0, ge=0, description="Estimated token count")
  focus_areas: list[str] = Field(
    default_factory=list, description="High-verbosity file paths"
  )


def is_text_file(file_path: str) -> bool:
  """
  Checks if a file is text by reading the first 1024 bytes
  and looking for null bytes.
  """
  try:
    with open(file_path, "rb") as f:
      chunk = f.read(1024)
    return b"\0" not in chunk
  except OSError:
    return False


def generate_repomap(
  root_dir: Path,
  token_limit: int = 2048,
  include_patterns: list[str] | None = None,
  exclude_patterns: list[str] | None = None,
  allowed_extensions: list[str] | None = None,
  use_gitignore: bool = True,
  use_default_excludes: bool = True,
  flight_plan: FlightPlan | None = None,
  show_costs: bool = False,
  strict: bool = False,
) -> MapResult | None:
  """
  Generate a repository map for a given directory.

  Args:
      root_dir: Root directory to map
      token_limit: Maximum token budget for the generated map
      include_patterns: Glob patterns to explicitly include
      exclude_patterns: Glob patterns to exclude
      allowed_extensions: Only include files with these extensions
      use_gitignore: Whether to respect .gitignore files
      use_default_excludes: Whether to use default exclusion patterns
      flight_plan: Optional FlightPlan configuration for multi-resolution rendering
      show_costs: Include cost annotations in output
      strict: Raise error if budget exceeded

  Returns:
      MapResult with content and files, or None if no files found
  """
  abs_root = root_dir.resolve()

  # --- Build Filter Specs ---
  specs: list[pathspec.PathSpec] = []

  # 1. Gitignore
  if use_gitignore:
    gitignore_path = abs_root / ".gitignore"
    if gitignore_path.exists():
      with gitignore_path.open("r") as f:
        specs.append(pathspec.PathSpec.from_lines("gitwildmatch", f.readlines()))

  # 2. User Excludes
  if exclude_patterns:
    specs.append(pathspec.PathSpec.from_lines("gitwildmatch", exclude_patterns))

  # 3. Default Excludes (Opinionated)
  default_exclude_spec = None
  if use_default_excludes:
    default_exclude_spec = pathspec.PathSpec.from_lines(
      "gitwildmatch", DEFAULT_EXCLUDE_PATTERNS
    )

  # 4. User Includes (Overrides excludes)
  include_spec = None
  if include_patterns:
    include_spec = pathspec.PathSpec.from_lines("gitwildmatch", include_patterns)

  # --- Walk and Collect ---
  fnames = []

  # Pre-format extensions for faster checking
  if allowed_extensions:
    allowed_extensions = [
      e if e.startswith(".") else f".{e}" for e in allowed_extensions
    ]

  for root, dirs, files in os.walk(abs_root):
    # A. Prune Directories
    for i in range(len(dirs) - 1, -1, -1):
      d = dirs[i]
      dir_rel = os.path.relpath(os.path.join(root, d), abs_root)

      # Default: Skip dot-directories (hidden) unless explicitly included
      if d.startswith(".") and d != ".":
        if include_spec and include_spec.match_file(dir_rel):
          pass  # Keep it
        else:
          dirs.pop(i)
          continue

      # Check specs
      if any(spec.match_file(dir_rel) for spec in specs):  # type: ignore[reportUnknownMemberType]
        dirs.pop(i)
        continue

      # Check default excludes
      if (
        default_exclude_spec
        and default_exclude_spec.match_file(dir_rel)
        and not (include_spec and include_spec.match_file(dir_rel))
      ):
        dirs.pop(i)

    for file in files:
      full_path = os.path.join(root, file)
      rel_path = os.path.relpath(full_path, abs_root)

      # --- Step 1: Check Inclusions (Highest Priority) ---
      is_explicitly_included = include_spec and include_spec.match_file(rel_path)

      if not is_explicitly_included:
        # --- Step 2: Check Extensions (If User Provided) ---
        if allowed_extensions and not any(
          file.endswith(ext) for ext in allowed_extensions
        ):
          continue

        # --- Step 3: Check Binary (First Principles: Don't map binaries) ---
        # We do this BEFORE excludes to save processing, or AFTER?
        # Doing it here ensures we don't accidentally include a binary
        # just because it passed the exclude list.
        if not is_text_file(full_path):
          continue

        # --- Step 4: Check Hard Excludes ---
        if any(spec.match_file(rel_path) for spec in specs):  # type: ignore[reportUnknownMemberType]
          continue

        # --- Step 5: Check Default Excludes ---
        if default_exclude_spec and default_exclude_spec.match_file(rel_path):
          continue

      fnames.append(rel_path)  # type: ignore[reportUnknownMemberType]

  if not fnames:
    return None

  # Convert relative paths to absolute for RepoMap
  abs_fnames = [str(abs_root / f) for f in fnames]

  # Use ContextRenderer if FlightPlan is provided
  if flight_plan:
    from repo_map.core.cost import estimate_tokens
    from repo_map.core.flight_plan import VerbosityLevel
    from repo_map.core.renderer import ContextRenderer

    renderer = ContextRenderer(flight_plan=flight_plan)

    # Read file contents
    files_with_content: list[tuple[str, str]] = []
    for rel_path in fnames:
      abs_path: Path = abs_root / rel_path  # type: ignore[assignment]
      try:
        content: str = abs_path.read_text(  # type: ignore[reportUnknownMemberType]
          encoding="utf-8", errors="replace"
        )
        files_with_content.append((rel_path, content))
      except OSError:
        continue

    if not files_with_content:
      return None

    # Render with context engine
    rendered = renderer.render(files_with_content, show_costs=show_costs, strict=strict)

    # Calculate metadata
    total_tokens = estimate_tokens(rendered)

    # Extract focus areas (files at high verbosity: INTERFACE or IMPLEMENTATION)
    focus_areas: list[str] = []
    for rel_path, _ in files_with_content:
      level = flight_plan.get_verbosity_for_path(rel_path)
      if level in (VerbosityLevel.INTERFACE, VerbosityLevel.IMPLEMENTATION):
        focus_areas.append(rel_path)

    return MapResult(
      content=rendered,
      files=fnames,
      total_tokens=total_tokens,
      focus_areas=focus_areas[:10],  # Limit to top 10
    )

  # Default: Use original RepoMap with PageRank
  from repo_map.core.cost import estimate_tokens as _estimate_tokens

  repo_map = RepoMap(
    root=str(abs_root),
    map_tokens=token_limit,
    verbose=False,
  )

  skeleton = repo_map.get_repo_map(abs_fnames)

  if not skeleton:
    return None

  return MapResult(
    content=skeleton,
    files=fnames,
    total_tokens=_estimate_tokens(skeleton),
  )
