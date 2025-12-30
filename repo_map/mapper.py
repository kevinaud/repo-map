import os
from dataclasses import dataclass
from pathlib import Path

import pathspec
from aider.io import InputOutput
from aider.models import Model
from aider.repomap import RepoMap

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


@dataclass
class MapResult:
  content: str
  files: list[str]


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


def generate_aider_repomap(
  root_dir: Path,
  token_limit: int = 2048,
  include_patterns: list[str] | None = None,
  exclude_patterns: list[str] | None = None,
  allowed_extensions: list[str] | None = None,
  use_gitignore: bool = True,
  use_default_excludes: bool = True,
  model_name: str = "gemini",
) -> MapResult | None:
  abs_root = root_dir.resolve()
  io = InputOutput(pretty=False, yes=True)
  main_model = Model(model_name)

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

  repo_map = RepoMap(
    map_tokens=token_limit,
    root=str(abs_root),
    main_model=main_model,
    io=io,
    verbose=False,
  )

  skeleton = repo_map.get_repo_map(chat_files=[], other_files=fnames)  # type: ignore[reportUnknownMemberType]

  if not skeleton:
    return None

  return MapResult(content=skeleton, files=fnames)
