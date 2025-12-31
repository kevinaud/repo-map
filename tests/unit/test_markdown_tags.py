"""Tests for markdown tag extraction."""

from repo_map.core.tags import get_tags_from_code


def test_markdown_headings_extracted():
  """Test that markdown headings are extracted as definitions."""
  markdown_content = """# Main Title

Some intro text.

## Section One

Content here.

### Subsection

More content.

## Section Two

Another section.
"""
  tags = list(get_tags_from_code("/tmp/test.md", "test.md", markdown_content))
  defs = [t for t in tags if t.kind == "def"]

  assert len(defs) == 4
  names = {t.name for t in defs}
  assert "Main Title" in names
  assert "Section One" in names
  assert "Subsection" in names
  assert "Section Two" in names


def test_markdown_code_block_language_as_reference():
  """Test that code block languages are extracted as references."""
  markdown_content = """# Example

```python
def example():
    pass
```

```javascript
console.log("hello");
```
"""
  tags = list(get_tags_from_code("/tmp/test.md", "test.md", markdown_content))
  refs = [t for t in tags if t.kind == "ref"]

  assert len(refs) == 2
  names = {t.name for t in refs}
  assert "python" in names
  assert "javascript" in names


def test_markdown_all_heading_levels():
  """Test that all heading levels (h1-h6) are extracted."""
  markdown_content = """# Heading 1
## Heading 2
### Heading 3
#### Heading 4
##### Heading 5
###### Heading 6
"""
  tags = list(get_tags_from_code("/tmp/test.md", "test.md", markdown_content))
  defs = [t for t in tags if t.kind == "def"]

  assert len(defs) == 6
  for i in range(1, 7):
    assert any(t.name == f"Heading {i}" for t in defs)


def test_markdown_empty_file():
  """Test that empty markdown file returns no tags."""
  tags = list(get_tags_from_code("/tmp/empty.md", "empty.md", ""))
  assert len(tags) == 0


def test_markdown_no_headings():
  """Test that markdown without headings returns no definition tags."""
  markdown_content = """Just some text without any headings.

More text here.

- A list item
- Another list item
"""
  tags = list(get_tags_from_code("/tmp/test.md", "test.md", markdown_content))
  defs = [t for t in tags if t.kind == "def"]
  assert len(defs) == 0
