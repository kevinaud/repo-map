"""
Repository map generation using PageRank-based ranking.

This module generates a concise "map" of a code repository by:
1. Extracting tags (definitions and references) from source files
2. Building a graph of relationships between files
3. Using PageRank to rank the most important definitions
4. Rendering a tree view of the most relevant code
"""

from __future__ import annotations

import math
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

import networkx as nx  # type: ignore[reportMissingTypeStubs]
from grep_ast import TreeContext  # type: ignore[reportMissingTypeStubs]
from tqdm import tqdm

from repo_map.core.special import filter_important_files
from repo_map.core.tags import Tag, get_tags_from_code

if TYPE_CHECKING:
  from collections.abc import Callable


class RepoMap:
  """
  Generates ranked repository maps using PageRank algorithm.

  The map shows the most important code definitions based on how they're
  referenced throughout the codebase.
  """

  def __init__(
    self,
    root: str | None = None,
    map_tokens: int = 1024,
    verbose: bool = False,
  ):
    """
    Initialize the RepoMap.

    Args:
        root: Root directory of the repository
        map_tokens: Maximum token budget for the generated map
        verbose: Whether to output verbose progress information
    """
    self.verbose = verbose
    self.root = root or os.getcwd()
    self.max_map_tokens = map_tokens

    self._tree_cache: dict[tuple[str, tuple[int, ...], float | None], str] = {}
    self._tree_context_cache: dict[str, dict[str, Any]] = {}
    self._warned_files: set[str] = set()

  def _estimate_tokens(self, text: str) -> int:
    """Estimate token count using character-based heuristic."""
    # Rough estimate: ~4 characters per token on average
    return len(text) // 4

  def _read_text(self, fname: str) -> str | None:
    """Read text content from a file."""
    try:
      with open(fname, encoding="utf-8", errors="ignore") as f:
        return f.read()
    except OSError:
      return None

  def _get_mtime(self, fname: str) -> float | None:
    """Get file modification time."""
    try:
      return os.path.getmtime(fname)
    except FileNotFoundError:
      return None

  def _get_rel_fname(self, fname: str) -> str:
    """Get relative path from root."""
    try:
      return os.path.relpath(fname, self.root)
    except ValueError:
      return fname

  def _get_tags(self, fname: str, rel_fname: str) -> list[Tag]:
    """Get tags for a file."""
    code = self._read_text(fname)
    if not code:
      return []

    return list(get_tags_from_code(fname, rel_fname, code))

  def _get_ranked_tags(
    self,
    fnames: list[str],
    progress: Callable[[str], None] | None = None,
  ) -> list[Tag | tuple[str]]:
    """
    Rank tags across files using PageRank algorithm.

    Args:
        fnames: List of file paths to analyze
        progress: Optional progress callback

    Returns:
        List of ranked tags, most important first
    """
    defines: dict[str, set[str]] = defaultdict(set)
    references: dict[str, list[str]] = defaultdict(list)
    definitions: dict[tuple[str, str], set[Tag]] = defaultdict(set)

    fnames = sorted(set(fnames))

    # Show progress bar for large repos
    if len(fnames) > 100:
      fnames_iter = tqdm(fnames, desc="Scanning repo")
      showing_bar = True
    else:
      fnames_iter = fnames
      showing_bar = False

    for fname in fnames_iter:
      if progress and not showing_bar:
        progress(f"Processing: {fname}")

      try:
        file_ok = Path(fname).is_file()
      except OSError:
        file_ok = False

      if not file_ok:
        if fname not in self._warned_files:
          self._warned_files.add(fname)
        continue

      rel_fname = self._get_rel_fname(fname)
      tags = self._get_tags(fname, rel_fname)

      for tag in tags:
        if tag.kind == "def":
          defines[tag.name].add(rel_fname)
          key = (rel_fname, tag.name)
          definitions[key].add(tag)
        elif tag.kind == "ref":
          references[tag.name].append(rel_fname)

    if not references:
      references = {k: list(v) for k, v in defines.items()}

    idents = set(defines.keys()).intersection(set(references.keys()))

    G: nx.MultiDiGraph[str] = nx.MultiDiGraph()

    # Add self-edges for definitions without references
    for ident in defines:
      if ident in references:
        continue
      for definer in defines[ident]:
        G.add_edge(definer, definer, weight=0.1, ident=ident)  # type: ignore[reportUnknownMemberType]

    for ident in idents:
      if progress:
        progress(f"Building graph: {ident}")

      definers = defines[ident]
      mul = 1.0

      # Boost multi-word identifiers (likely more meaningful)
      is_snake = ("_" in ident) and any(c.isalpha() for c in ident)
      is_kebab = ("-" in ident) and any(c.isalpha() for c in ident)
      is_camel = any(c.isupper() for c in ident) and any(c.islower() for c in ident)
      if (is_snake or is_kebab or is_camel) and len(ident) >= 8:
        mul *= 10
      if ident.startswith("_"):
        mul *= 0.1
      if len(defines[ident]) > 5:
        mul *= 0.1

      for referencer, num_refs in Counter(references[ident]).items():
        for definer in definers:
          # Scale down high frequency mentions
          num_refs_scaled = math.sqrt(num_refs)
          G.add_edge(  # type: ignore[reportUnknownMemberType]
            referencer, definer, weight=mul * num_refs_scaled, ident=ident
          )

    try:
      ranked: dict[str, float] = nx.pagerank(G, weight="weight")
    except ZeroDivisionError:
      try:
        ranked = nx.pagerank(G, weight="weight")
      except ZeroDivisionError:
        return []

    # Distribute rank from each source node across its out edges
    ranked_definitions: dict[tuple[str, str], float] = defaultdict(float)
    for src in G.nodes:  # type: ignore[reportUnknownMemberType]
      if progress:
        progress(f"Ranking: {src}")

      src_rank = ranked[src]
      total_weight = sum(  # type: ignore[reportUnknownMemberType]
        data["weight"] for _, _, data in G.out_edges(src, data=True)
      )
      if total_weight == 0:
        continue

      for _, dst, data in G.out_edges(src, data=True):  # type: ignore[reportUnknownMemberType]
        data["rank"] = src_rank * data["weight"] / total_weight
        ident = data["ident"]
        ranked_definitions[(dst, ident)] += data["rank"]

    ranked_tags: list[Tag | tuple[str]] = []
    sorted_definitions = sorted(
      ranked_definitions.items(), reverse=True, key=lambda x: (x[1], x[0])
    )

    for (fname, ident), _ in sorted_definitions:
      ranked_tags += list(definitions.get((fname, ident), []))

    # Add files that have no tags
    rel_fnames = {self._get_rel_fname(fname) for fname in fnames}
    fnames_already_included = {rt[0] for rt in ranked_tags}

    top_rank = sorted([(rank, node) for node, rank in ranked.items()], reverse=True)
    for _, fname in top_rank:
      if fname in rel_fnames:
        rel_fnames.discard(fname)
      if fname not in fnames_already_included:
        ranked_tags.append((fname,))

    for fname in rel_fnames:
      ranked_tags.append((fname,))

    return ranked_tags

  def _render_tree(self, abs_fname: str, rel_fname: str, lois: list[int]) -> str:
    """Render a tree view of specific lines of interest in a file."""
    mtime = self._get_mtime(abs_fname)
    key = (rel_fname, tuple(sorted(lois)), mtime)

    if key in self._tree_cache:
      return self._tree_cache[key]

    if (
      rel_fname not in self._tree_context_cache
      or self._tree_context_cache[rel_fname]["mtime"] != mtime
    ):
      code = self._read_text(abs_fname) or ""
      if not code.endswith("\n"):
        code += "\n"

      context = TreeContext(
        rel_fname,
        code,
        color=False,
        line_number=False,
        child_context=False,
        last_line=False,
        margin=0,
        mark_lois=False,
        loi_pad=0,
        show_top_of_file_parent_scope=False,
      )
      self._tree_context_cache[rel_fname] = {"context": context, "mtime": mtime}

    context = self._tree_context_cache[rel_fname]["context"]
    context.lines_of_interest = set()
    context.add_lines_of_interest(lois)
    context.add_context()
    res: str = context.format()
    self._tree_cache[key] = res
    return res

  def _to_tree(self, tags: list[Tag | tuple[str]]) -> str:
    """Convert ranked tags to a tree representation."""
    if not tags:
      return ""

    cur_fname: str | None = None
    cur_abs_fname: str | None = None
    lois: list[int] | None = None
    output = ""

    # Add dummy tag to flush final entry
    dummy_tag: tuple[None] = (None,)
    for tag in [*sorted(tags), dummy_tag]:  # type: ignore[operator]
      this_rel_fname: str | None = tag[0]

      if this_rel_fname != cur_fname:
        if lois is not None and cur_abs_fname and cur_fname:
          output += "\n"
          output += cur_fname + ":\n"
          output += self._render_tree(cur_abs_fname, cur_fname, lois)
          lois = None
        elif cur_fname:
          output += "\n" + cur_fname + "\n"

        if isinstance(tag, Tag):
          lois = []
          cur_abs_fname = tag.fname
        cur_fname = this_rel_fname

      if lois is not None and isinstance(tag, Tag):
        lois.append(tag.line)

    # Truncate long lines (e.g., minified JS)
    return "\n".join([line[:100] for line in output.splitlines()]) + "\n"

  def get_repo_map(self, fnames: list[str]) -> str | None:
    """
    Generate a repository map for the given files.

    Args:
        fnames: List of file paths to include in the map

    Returns:
        A string containing the repo map, or None if no map could be generated
    """
    if self.max_map_tokens <= 0:
      return None
    if not fnames:
      return None

    max_map_tokens = self.max_map_tokens

    try:
      ranked_tags = self._get_ranked_tags(fnames)
    except RecursionError:
      return None

    # Prioritize important/special files
    rel_fnames = sorted({self._get_rel_fname(fname) for fname in fnames})
    special_fnames = filter_important_files(rel_fnames)
    ranked_tags_fnames = {tag[0] for tag in ranked_tags}
    special_fnames = [fn for fn in special_fnames if fn not in ranked_tags_fnames]
    special_fnames_tuples = [(fn,) for fn in special_fnames]

    ranked_tags = special_fnames_tuples + ranked_tags  # type: ignore[operator]

    # Binary search for optimal number of tags to fit token budget
    num_tags = len(ranked_tags)
    lower_bound = 0
    upper_bound = num_tags
    best_tree: str | None = None
    best_tree_tokens = 0

    self._tree_cache = {}

    middle = min(int(max_map_tokens // 25), num_tags)
    while lower_bound <= upper_bound:
      tree = self._to_tree(ranked_tags[:middle])
      num_tokens = self._estimate_tokens(tree)

      pct_err = (
        abs(num_tokens - max_map_tokens) / max_map_tokens if max_map_tokens else 0
      )
      ok_err = 0.15
      is_better = num_tokens <= max_map_tokens and num_tokens > best_tree_tokens
      if is_better or pct_err < ok_err:
        best_tree = tree
        best_tree_tokens = num_tokens

        if pct_err < ok_err:
          break

      if num_tokens < max_map_tokens:
        lower_bound = middle + 1
      else:
        upper_bound = middle - 1

      middle = (lower_bound + upper_bound) // 2

    return best_tree
