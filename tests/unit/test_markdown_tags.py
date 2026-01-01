"""Unit tests for markdown tag extraction."""

from __future__ import annotations

import pytest

from repo_map.core.tags import get_tags_from_code


class TestMarkdownTagExtraction:
  """Tests for extracting tags from markdown files."""

  @pytest.fixture
  def markdown_with_headings(self) -> str:
    """Sample markdown with nested headings."""
    return """# Main Title

Some intro text.

## Section One

Content here.

### Subsection

More content.

## Section Two

Another section.
"""

  @pytest.fixture
  def markdown_with_code_blocks(self) -> str:
    """Sample markdown with fenced code blocks."""
    return """# Example

```python
def example():
    pass
```

```javascript
console.log("hello");
```
"""

  @pytest.fixture
  def markdown_all_heading_levels(self) -> str:
    """Markdown with all heading levels h1-h6."""
    return """# Heading 1
## Heading 2
### Heading 3
#### Heading 4
##### Heading 5
###### Heading 6
"""

  def test_headings_extracted_as_definitions(self, markdown_with_headings: str) -> None:
    """Should extract markdown headings as definition tags."""
    tags = list(get_tags_from_code("/tmp/test.md", "test.md", markdown_with_headings))
    defs = [t for t in tags if t.kind == "def"]

    assert len(defs) == 4
    names = {t.name for t in defs}
    assert "Main Title" in names
    assert "Section One" in names
    assert "Subsection" in names
    assert "Section Two" in names

  def test_code_block_languages_extracted_as_references(
    self, markdown_with_code_blocks: str
  ) -> None:
    """Should extract code block languages as reference tags."""
    tags = list(
      get_tags_from_code("/tmp/test.md", "test.md", markdown_with_code_blocks)
    )
    refs = [t for t in tags if t.kind == "ref"]

    assert len(refs) == 2
    names = {t.name for t in refs}
    assert "python" in names
    assert "javascript" in names

  def test_all_heading_levels_extracted(self, markdown_all_heading_levels: str) -> None:
    """Should extract all heading levels h1-h6."""
    tags = list(
      get_tags_from_code("/tmp/test.md", "test.md", markdown_all_heading_levels)
    )
    defs = [t for t in tags if t.kind == "def"]

    assert len(defs) == 6
    for i in range(1, 7):
      assert any(t.name == f"Heading {i}" for t in defs)

  def test_empty_file_returns_no_tags(self) -> None:
    """Should return no tags for empty markdown file."""
    tags = list(get_tags_from_code("/tmp/empty.md", "empty.md", ""))
    assert len(tags) == 0

  def test_no_headings_returns_no_definitions(self) -> None:
    """Should return no definitions for markdown without headings."""
    markdown_content = """Just some text without any headings.

More text here.

- A list item
- Another list item
"""
    tags = list(get_tags_from_code("/tmp/test.md", "test.md", markdown_content))
    defs = [t for t in tags if t.kind == "def"]
    assert len(defs) == 0
