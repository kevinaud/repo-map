"""
Tag extraction from source files using tree-sitter.

Extracts definitions (functions, classes, methods, etc.) and references
from source code files.
"""

from __future__ import annotations

import warnings
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
  from collections.abc import Iterator

from grep_ast import filename_to_lang  # type: ignore[reportMissingTypeStubs]
from pygments.lexers import guess_lexer_for_filename
from pygments.token import Token

# tree_sitter is throwing a FutureWarning
warnings.simplefilter("ignore", category=FutureWarning)
from grep_ast.tsl import (  # type: ignore[reportMissingTypeStubs]  # noqa: E402
  USING_TSL_PACK,
  get_language,
  get_parser,
)


class Tag(NamedTuple):
  """Represents a tag (definition or reference) in a source file."""

  rel_fname: str
  fname: str
  line: int
  name: str
  kind: str  # "def" or "ref"


def get_scm_fname(lang: str) -> Path | None:
  """Get the path to the tree-sitter query file for a language."""
  try:
    path = resources.files("repo_map.core").joinpath(
      "queries",
      "tree-sitter-language-pack",
      f"{lang}-tags.scm",
    )
    if path.is_file():
      return Path(str(path))
  except (KeyError, TypeError, FileNotFoundError):
    pass

  return None


def get_tags_from_code(
  fname: str,
  rel_fname: str,
  code: str,
) -> Iterator[Tag]:
  """
  Extract tags (definitions and references) from source code.

  Uses tree-sitter for parsing when available, falls back to pygments
  for reference extraction when tree-sitter doesn't provide refs.

  Args:
      fname: Absolute path to the file
      rel_fname: Relative path to the file (for display)
      code: Source code content

  Yields:
      Tag objects representing definitions and references
  """
  lang = filename_to_lang(fname)
  if not lang:
    return

  try:
    language: Any = get_language(lang)  # type: ignore[reportArgumentType]
    parser: Any = get_parser(lang)  # type: ignore[reportArgumentType]
  except Exception:
    return

  query_scm_path = get_scm_fname(lang)
  if not query_scm_path or not query_scm_path.exists():
    return

  query_scm = query_scm_path.read_text()
  tree = parser.parse(bytes(code, "utf-8"))

  # Run the tags queries
  query = language.query(query_scm)
  captures = query.captures(tree.root_node)

  saw: set[str] = set()
  all_nodes: list[tuple[Any, str]]
  if USING_TSL_PACK:
    all_nodes = []
    for tag, nodes in captures.items():
      all_nodes += [(node, tag) for node in nodes]
  else:
    all_nodes = list(captures)

  for node, tag in all_nodes:
    if tag.startswith("name.definition."):
      kind = "def"
    elif tag.startswith("name.reference."):
      kind = "ref"
    else:
      continue

    saw.add(kind)

    yield Tag(
      rel_fname=rel_fname,
      fname=fname,
      name=node.text.decode("utf-8"),
      kind=kind,
      line=node.start_point[0],
    )

  if "ref" in saw:
    return
  if "def" not in saw:
    return

  # We saw defs, without any refs
  # Some tags files only provide defs (cpp, for example)
  # Use pygments to backfill refs
  try:
    lexer = guess_lexer_for_filename(fname, code)
  except Exception:
    return

  tokens = list(lexer.get_tokens(code))
  tokens = [token[1] for token in tokens if token[0] in Token.Name]

  for token in tokens:
    yield Tag(
      rel_fname=rel_fname,
      fname=fname,
      name=token,
      kind="ref",
      line=-1,
    )
