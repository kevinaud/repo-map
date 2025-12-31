"""
Example implementation for multi-resolution code extraction using tree-sitter.

This demonstrates how to:
1. Run tree-sitter queries for different verbosity levels
2. Reconstruct interface-level output from captured components
3. Handle Python and Markdown specifically
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from collections.abc import Iterator


class VerbosityLevel(Enum):
  """Extraction verbosity levels."""

  STRUCTURE = auto()  # Level 2: Names only
  INTERFACE = auto()  # Level 3: Signatures + docstrings
  FULL = auto()  # Level 4: Complete file content


@dataclass
class ExtractedDefinition:
  """A definition extracted from source code."""

  name: str
  kind: str  # "function", "class", "method", "heading", etc.
  line: int
  signature: str | None = None  # Full signature line
  docstring: str | None = None  # Documentation string
  decorators: list[str] | None = None  # For Python
  level: int | None = None  # For markdown headings


def extract_python_interface(node, source_bytes: bytes) -> str:
  """
  Extract interface-level representation of a Python function or class.

  This demonstrates the key technique: capture the whole node with tree-sitter,
  then selectively reconstruct only the interface parts.

  Args:
      node: A tree-sitter node (function_definition or class_definition)
      source_bytes: The source file bytes

  Returns:
      String containing the interface (signature + docstring)
  """
  lines = []

  # Handle decorated definitions
  if node.parent and node.parent.type == "decorated_definition":
    # Include decorators
    for child in node.parent.children:
      if child.type == "decorator":
        lines.append(get_node_text(child, source_bytes))

  if node.type == "function_definition":
    lines.append(_extract_function_signature(node, source_bytes))
    docstring = _extract_docstring(node, source_bytes)
    if docstring:
      lines.append(f"    {docstring}")

  elif node.type == "class_definition":
    lines.append(_extract_class_signature(node, source_bytes))
    docstring = _extract_docstring(node, source_bytes)
    if docstring:
      lines.append(f"    {docstring}")
    # Also extract method signatures
    body = node.child_by_field_name("body")
    if body:
      for child in body.children:
        if child.type == "function_definition":
          lines.append("")
          lines.append("    " + _extract_function_signature(child, source_bytes))
          method_doc = _extract_docstring(child, source_bytes)
          if method_doc:
            # Indent docstring for method
            indented = "\n".join("        " + line for line in method_doc.split("\n"))
            lines.append(indented)

  return "\n".join(lines)


def _extract_function_signature(node, source_bytes: bytes) -> str:
  """Extract just the signature line from a function definition."""
  parts = []

  for child in node.children:
    if child.type == "async":
      parts.append("async")
    elif child.type == "def":
      parts.append("def")
    elif child.type == "name" or child.type == "parameters":
      parts.append(get_node_text(child, source_bytes))
    elif child.type == "->":
      parts.append("->")
    elif child.type == "return_type" or child.type == "type":
      parts.append(get_node_text(child, source_bytes))
    elif child.type == ":":
      parts.append(":")
      break  # Stop before body

  return " ".join(parts)


def _extract_class_signature(node, source_bytes: bytes) -> str:
  """Extract just the signature line from a class definition."""
  parts = ["class"]

  for child in node.children:
    if (
      child.type == "name"
      or child.type == "type_parameters"
      or child.type == "argument_list"
    ):
      parts.append(get_node_text(child, source_bytes))
    elif child.type == ":":
      parts.append(":")
      break

  return " ".join(parts)


def _extract_docstring(node, source_bytes: bytes) -> str | None:
  """
  Extract docstring from a function or class definition.

  The docstring is the first expression_statement containing a string
  in the body block.
  """
  body = node.child_by_field_name("body")
  if not body or not body.children:
    return None

  # Look for first expression_statement with a string
  for child in body.children:
    if child.type == "expression_statement":
      for expr_child in child.children:
        if expr_child.type == "string":
          return get_node_text(expr_child, source_bytes)
      break  # Only check first expression_statement
    if child.type not in ("comment", "pass_statement"):
      # If first statement isn't a string, there's no docstring
      break

  return None


def get_node_text(node, source_bytes: bytes) -> str:
  """Get the text content of a node."""
  return source_bytes[node.start_byte : node.end_byte].decode("utf-8")


# ============================================================
# MARKDOWN EXTRACTION
# ============================================================


def extract_markdown_structure(
  tree, source_bytes: bytes, level: VerbosityLevel
) -> Iterator[ExtractedDefinition]:
  """
  Extract structure from a Markdown document.

  Args:
      tree: Parsed tree-sitter tree
      source_bytes: Source file bytes
      level: Extraction verbosity level

  Yields:
      ExtractedDefinition objects for headings (and optionally paragraphs)
  """
  for node in _walk_tree(tree.root_node):
    if node.type == "atx_heading":
      heading_level = _get_heading_level(node)
      heading_text = _get_heading_text(node, source_bytes)

      defn = ExtractedDefinition(
        name=heading_text,
        kind="heading",
        line=node.start_point[0] + 1,
        level=heading_level,
      )

      if level == VerbosityLevel.INTERFACE:
        # Also capture first paragraph after heading
        next_para = _get_next_paragraph(node, source_bytes)
        if next_para:
          defn.docstring = next_para

      yield defn

    elif node.type == "setext_heading":
      heading_text = _get_setext_heading_text(node, source_bytes)

      defn = ExtractedDefinition(
        name=heading_text,
        kind="heading",
        line=node.start_point[0] + 1,
        level=1,  # Setext = h1 or h2
      )

      if level == VerbosityLevel.INTERFACE:
        next_para = _get_next_paragraph(node, source_bytes)
        if next_para:
          defn.docstring = next_para

      yield defn


def _walk_tree(node) -> Iterator:
  """Walk all nodes in the tree."""
  yield node
  for child in node.children:
    yield from _walk_tree(child)


def _get_heading_level(node) -> int:
  """Get the level (1-6) of an ATX heading."""
  for child in node.children:
    if child.type.startswith("atx_h") and child.type.endswith("_marker"):
      # atx_h1_marker -> 1, atx_h2_marker -> 2, etc.
      return int(child.type[5])  # Extract digit
  return 1


def _get_heading_text(node, source_bytes: bytes) -> str:
  """Get the text content of an ATX heading."""
  for child in node.children:
    if child.type == "inline":
      return get_node_text(child, source_bytes).strip()
  return ""


def _get_setext_heading_text(node, source_bytes: bytes) -> str:
  """Get the text content of a Setext heading."""
  for child in node.children:
    if child.type == "paragraph":
      for para_child in child.children:
        if para_child.type == "inline":
          return get_node_text(para_child, source_bytes).strip()
  return ""


def _get_next_paragraph(heading_node, source_bytes: bytes) -> str | None:
  """
  Get the first paragraph following a heading.

  Strategy: Look at siblings in the parent node.
  """
  parent = heading_node.parent
  if not parent:
    return None

  found_heading = False
  for sibling in parent.children:
    if sibling == heading_node:
      found_heading = True
      continue
    if found_heading:
      if sibling.type == "paragraph":
        return get_node_text(sibling, source_bytes).strip()
      if sibling.type in ("atx_heading", "setext_heading"):
        # Hit next heading, no paragraph between
        return None

  return None


# ============================================================
# QUERY-BASED APPROACH (alternative)
# ============================================================


PYTHON_LEVEL2_QUERY = """
; Structure only - names
(class_definition
  name: (identifier) @name.definition.class)

(function_definition
  name: (identifier) @name.definition.function)
"""

PYTHON_LEVEL3_QUERY = """
; Interface - capture components for reconstruction
(function_definition) @definition.function

(function_definition
  name: (identifier) @name.function)

(function_definition
  parameters: (parameters) @signature.parameters)

(function_definition
  return_type: (type) @signature.return_type)

(function_definition
  body: (block
    .
    (expression_statement
      (string) @docstring.function)))

(class_definition) @definition.class

(class_definition
  name: (identifier) @name.class)

(class_definition
  body: (block
    .
    (expression_statement
      (string) @docstring.class)))

(decorated_definition
  (decorator) @decorator)
"""


def run_query_extraction(
  tree, language, query_string: str, source_bytes: bytes
) -> dict:
  """
  Run a tree-sitter query and organize captures by type.

  Returns:
      Dict mapping capture names to lists of (node, text) tuples
  """
  query = language.query(query_string)
  captures = query.captures(tree.root_node)

  results: dict[str, list] = {}

  # Handle both old and new tree-sitter-python API
  if isinstance(captures, dict):
    # New API: captures is {name: [nodes]}
    for name, nodes in captures.items():
      results[name] = [(node, get_node_text(node, source_bytes)) for node in nodes]
  else:
    # Old API: captures is [(node, name), ...]
    for node, name in captures:
      if name not in results:
        results[name] = []
      results[name].append((node, get_node_text(node, source_bytes)))

  return results


# ============================================================
# EXAMPLE USAGE
# ============================================================

if __name__ == "__main__":
  # Example Python code
  python_code = '''
@dataclass
class User:
    """A user in the system."""
    name: str
    age: int

    def greet(self, greeting: str = "Hello") -> str:
        """Return a greeting message."""
        return f"{greeting}, {self.name}!"

def process_users(users: list[User]) -> None:
    """Process a list of users."""
    for user in users:
        print(user.greet())
'''

  print("=== Python Code Analysis ===")
  print("\nLevel 2 (Structure) would output:")
  print("  class User")
  print("  def greet")
  print("  def process_users")

  print("\nLevel 3 (Interface) would output:")
  print(
    """
@dataclass
class User:
    \"\"\"A user in the system.\"\"\"

    def greet(self, greeting: str = "Hello") -> str:
        \"\"\"Return a greeting message.\"\"\"

def process_users(users: list[User]) -> None:
    \"\"\"Process a list of users.\"\"\"
"""
  )

  # Example Markdown
  markdown_code = """
# Project Overview

This tool generates repository maps for LLMs.

## Features

- Multi-resolution extraction
- Tree-sitter based parsing

### Level 2

Structure only.

### Level 3

Interface level.

## Usage

Run with `repo-map generate .`
"""

  print("\n=== Markdown Analysis ===")
  print("\nLevel 2 (Structure) would output:")
  print("  # Project Overview")
  print("  ## Features")
  print("  ### Level 2")
  print("  ### Level 3")
  print("  ## Usage")

  print("\nLevel 3 (Interface) would output:")
  print(
    """
# Project Overview

This tool generates repository maps for LLMs.

## Features

- Multi-resolution extraction

### Level 2

Structure only.

### Level 3

Interface level.

## Usage

Run with `repo-map generate .`
"""
  )
