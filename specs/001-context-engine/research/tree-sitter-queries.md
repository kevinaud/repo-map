# Tree-Sitter Query Research: Multi-Resolution Code Extraction

## Summary

This document provides tree-sitter query patterns for extracting code at different verbosity levels (Level 2: Structure, Level 3: Interface) for Python and Markdown.

## Key Tree-Sitter Query Syntax Elements

### Anchors (`.` operator)
- `. (node)` - Match only first child
- `(node) .` - Match only last child  
- `(node) . (node)` - Match immediate siblings

### Captures (`@name`)
- `@definition.function` - Capture whole function definition
- `@name` - Capture just the identifier

### Field Access (`field: node`)
- `name: (identifier)` - Match specific named field
- `body: (block)` - Match body field

### Negated Fields (`!field`)
- `!type_parameters` - Match nodes WITHOUT this field

### Quantifiers
- `(node)+` - One or more
- `(node)*` - Zero or more
- `(node)?` - Optional

### Alternations (`[]`)
- `[node_a node_b]` - Match either

---

## Python Tree-Sitter Node Structure

Key node types for multi-resolution extraction:

```
function_definition
├── name: (identifier)
├── parameters: (parameters)
│   ├── (identifier)
│   ├── (default_parameter)
│   ├── (typed_parameter)
│   ├── (list_splat_pattern)      # *args
│   └── (dictionary_splat_pattern) # **kwargs
├── return_type: (type)?
├── body: (block)
│   ├── (expression_statement (string))  # docstring if first
│   └── ... other statements

class_definition
├── name: (identifier)
├── type_parameters: (type_parameter)?
├── superclasses: (argument_list)?
├── body: (block)
│   ├── (expression_statement (string))  # docstring if first
│   └── ... methods, attributes
```

---

## Python Level 2: Structure Only

**Goal**: Extract only class/function names, no signatures or bodies.

```scheme
; python-level2-tags.scm
; ======================
; Level 2: Structure only - class names and function names

; Module-level assignments (constants)
(module
  (expression_statement
    (assignment
      left: (identifier) @name.definition.constant) @definition.constant))

; Class definitions - name only
(class_definition
  name: (identifier) @name.definition.class) @definition.class

; Function definitions - name only
(function_definition
  name: (identifier) @name.definition.function) @definition.function
```

**Output format** (post-processing required):
```
class MyClass
def my_function
def my_method
```

---

## Python Level 3: Interface (Signature + Docstring)

**Goal**: Extract class/function names + full signatures + docstrings, WITHOUT implementation bodies.

### Challenge: Tree-sitter captures whole nodes

Tree-sitter doesn't have a "capture node without children" feature. The `@definition.function` capture on `function_definition` includes the entire body. 

### Solution Strategy

**Approach 1: Capture components separately**

```scheme
; python-level3-tags.scm
; ======================
; Level 3: Interface - signatures and docstrings

; ----- FUNCTIONS -----

; Capture function name
(function_definition
  name: (identifier) @name.definition.function)

; Capture full parameter list (including type hints)
(function_definition
  parameters: (parameters) @signature.parameters)

; Capture return type annotation
(function_definition
  return_type: (type) @signature.return_type)

; Capture docstring - first string in body
(function_definition
  body: (block
    . (expression_statement
        (string) @docstring.function)))

; Capture decorators
(decorated_definition
  (decorator) @decorator
  definition: (function_definition))


; ----- CLASSES -----

; Capture class name
(class_definition
  name: (identifier) @name.definition.class)

; Capture class inheritance
(class_definition
  superclasses: (argument_list) @signature.superclasses)

; Capture class type parameters
(class_definition
  type_parameters: (type_parameter) @signature.type_parameters)

; Capture class docstring - first string in body
(class_definition
  body: (block
    . (expression_statement
        (string) @docstring.class)))

; Capture class decorators
(decorated_definition
  (decorator) @decorator
  definition: (class_definition))


; ----- METHOD SIGNATURES (inside classes) -----

; Method name within class
(class_definition
  body: (block
    (function_definition
      name: (identifier) @name.definition.method)))

; Method parameters within class
(class_definition
  body: (block
    (function_definition
      parameters: (parameters) @signature.method_parameters)))

; Method return type within class
(class_definition
  body: (block
    (function_definition
      return_type: (type) @signature.method_return_type)))

; Method docstring within class
(class_definition
  body: (block
    (function_definition
      body: (block
        . (expression_statement
            (string) @docstring.method)))))
```

**Approach 2: Capture whole definition and reconstruct in code**

The simpler approach for implementation: capture the whole `function_definition` or `class_definition` node, then use node position/children to reconstruct only the interface portion:

```scheme
; Capture full nodes for post-processing
(function_definition) @definition.function

(class_definition) @definition.class
```

Then in code:
```python
def extract_interface(node):
    """Extract interface from function/class definition."""
    if node.type == "function_definition":
        # Get: def name(params) -> return_type:
        # Then get first child of body if it's a string (docstring)
        parts = []
        for child in node.children:
            if child.type == "body":
                # Only include docstring from body
                block = child
                if block.children:
                    first_stmt = block.children[0]
                    if first_stmt.type == "expression_statement":
                        expr = first_stmt.children[0]
                        if expr.type == "string":
                            parts.append(expr.text)
                break
            else:
                parts.append(child.text)
        return b" ".join(parts)
```

---

## Python Examples

### Input
```python
@dataclass
class User:
    """A user in the system.
    
    Attributes:
        name: The user's full name
        age: The user's age in years
    """
    name: str
    age: int
    
    def greet(self, greeting: str = "Hello") -> str:
        """Return a greeting message.
        
        Args:
            greeting: The greeting word to use
            
        Returns:
            A personalized greeting string
        """
        return f"{greeting}, {self.name}!"
```

### Level 2 Output
```
class User
def greet
```

### Level 3 Output
```python
@dataclass
class User:
    """A user in the system.
    
    Attributes:
        name: The user's full name
        age: The user's age in years
    """

    def greet(self, greeting: str = "Hello") -> str:
        """Return a greeting message.
        
        Args:
            greeting: The greeting word to use
            
        Returns:
            A personalized greeting string
        """
```

---

## Markdown Tree-Sitter Node Structure

Using `tree-sitter-markdown` (MDeiml version), the structure is:

```
document
├── section
│   ├── atx_heading
│   │   ├── atx_h1_marker / atx_h2_marker / etc
│   │   └── inline (heading text)
│   ├── paragraph
│   │   └── inline (paragraph text)
│   ├── section (nested)
│   │   └── ...
│   ├── fenced_code_block
│   ├── list
│   └── ...
```

**Note**: The `section` node groups a heading with its content until the next same-or-higher-level heading.

---

## Markdown Level 2: Structure (Headings Only)

**Goal**: Extract document outline - all headings at all levels.

```scheme
; markdown-level2-tags.scm
; ========================
; Level 2: Structure - headings only

; ATX headings (# style)
(atx_heading
  (atx_h1_marker)
  (inline) @name.definition.heading.h1) @definition.heading

(atx_heading
  (atx_h2_marker)
  (inline) @name.definition.heading.h2) @definition.heading

(atx_heading
  (atx_h3_marker)
  (inline) @name.definition.heading.h3) @definition.heading

(atx_heading
  (atx_h4_marker)
  (inline) @name.definition.heading.h4) @definition.heading

(atx_heading
  (atx_h5_marker)
  (inline) @name.definition.heading.h5) @definition.heading

(atx_heading
  (atx_h6_marker)
  (inline) @name.definition.heading.h6) @definition.heading

; Setext headings (underlined with === or ---)
(setext_heading
  (paragraph
    (inline) @name.definition.heading)) @definition.heading
```

---

## Markdown Level 3: Interface (Headings + First Paragraph)

**Goal**: Extract headings plus the first paragraph after each heading (the "summary" or "lead").

### Challenge: Capturing siblings

Tree-sitter queries can capture siblings but relating "this paragraph belongs to that heading" requires either:
1. The `section` grouping node (if available in the grammar)
2. Post-processing with position tracking

### Solution using section nodes (if available)

```scheme
; markdown-level3-tags.scm
; ========================
; Level 3: Headings + first paragraph (summary)

; Heading text
(atx_heading
  [(atx_h1_marker) (atx_h2_marker) (atx_h3_marker) 
   (atx_h4_marker) (atx_h5_marker) (atx_h6_marker)]
  (inline) @content.heading) @definition.heading

; First paragraph after heading in a section
(section
  (atx_heading) @context.heading
  . (paragraph) @content.first_paragraph)

; Setext heading with following paragraph
(section
  (setext_heading) @context.heading  
  . (paragraph) @content.first_paragraph)
```

### Alternative: Capture all, filter in code

```scheme
; Capture all headings and all paragraphs
(atx_heading) @heading
(setext_heading) @heading  
(paragraph) @paragraph
```

Then in code, match paragraphs to their preceding headings by line number.

---

## Markdown Examples

### Input
```markdown
# Project Overview

This is a tool for generating repository maps.

It uses tree-sitter for parsing.

## Features

Multi-resolution extraction allows you to control verbosity.

### Level 2 - Structure
Names only.

### Level 3 - Interface  
Includes signatures and docstrings.

## Usage

Run with: `repo-map generate .`
```

### Level 2 Output
```
# Project Overview
## Features
### Level 2 - Structure
### Level 3 - Interface
## Usage
```

### Level 3 Output
```markdown
# Project Overview

This is a tool for generating repository maps.

## Features

Multi-resolution extraction allows you to control verbosity.

### Level 2 - Structure

Names only.

### Level 3 - Interface

Includes signatures and docstrings.

## Usage

Run with: `repo-map generate .`
```

---

## Implementation Recommendations

### 1. Use Component Captures + Code Reconstruction

Rather than trying to do everything in the query, capture individual components and reconstruct in code:

```python
class InterfaceExtractor:
    """Extract interface-level code from tree-sitter nodes."""
    
    def __init__(self, source_bytes: bytes):
        self.source = source_bytes
        
    def extract_function_interface(self, node) -> str:
        """Extract function signature + docstring."""
        parts = []
        
        # Get decorators if wrapped in decorated_definition
        if node.parent and node.parent.type == "decorated_definition":
            for child in node.parent.children:
                if child.type == "decorator":
                    parts.append(self.get_text(child))
        
        # Build signature line
        sig_parts = ["def"]
        for child in node.children:
            if child.type == "name":
                sig_parts.append(self.get_text(child))
            elif child.type == "parameters":
                sig_parts.append(self.get_text(child))
            elif child.type == "return_type":
                sig_parts.append("->")
                sig_parts.append(self.get_text(child))
            elif child.type == ":":
                sig_parts.append(":")
                break
        
        parts.append(" ".join(sig_parts))
        
        # Get docstring from body
        body = node.child_by_field_name("body")
        if body and body.children:
            first_stmt = body.children[0]
            if first_stmt.type == "expression_statement":
                expr = first_stmt.children[0] if first_stmt.children else None
                if expr and expr.type == "string":
                    parts.append("    " + self.get_text(expr))
        
        return "\n".join(parts)
```

### 2. Query Strategy by Level

| Level | Query Approach | Post-Processing |
|-------|---------------|-----------------|
| 2 (Structure) | Capture `@name.definition.*` only | Simple: just emit names |
| 3 (Interface) | Capture full nodes OR components | Reconstruct signature + docstring |
| 4 (Full) | No query needed | Read raw file content |

### 3. Handle Language-Specific Differences

Different languages have different conventions:
- **Python**: Docstrings are string literals in body
- **JavaScript/TypeScript**: JSDoc comments precede functions
- **Go**: Doc comments are regular comments preceding declarations
- **Rust**: `///` doc comments precede items

Create language-specific extractors that understand these patterns.

---

## Limitations and Workarounds

### Limitation 1: No "exclude children" in queries

Tree-sitter queries capture whole nodes. You cannot say "capture this node but not its body child."

**Workaround**: Capture the node, then use node traversal in code to extract only the parts you want.

### Limitation 2: Sibling relationships require careful anchoring

Getting "the paragraph after this heading" requires using the `.` anchor operator carefully, or having a grouping node like `section`.

**Workaround**: Capture all relevant nodes with position info, then match them in code based on line numbers.

### Limitation 3: Multi-line string handling

Docstrings can be triple-quoted and span many lines. The query captures the whole string node.

**Workaround**: This is actually fine for our purposes - we want the whole docstring.

### Limitation 4: Decorator association

Python decorators create a `decorated_definition` wrapper node. The function itself doesn't "know" about its decorators.

**Workaround**: When processing a function, check if its parent is `decorated_definition` and include those decorators.

---

## References

- [Tree-sitter Query Syntax](https://tree-sitter.github.io/tree-sitter/using-parsers/queries/1-syntax.html)
- [Tree-sitter Query Operators](https://tree-sitter.github.io/tree-sitter/using-parsers/queries/2-operators.html)
- [nvim-treesitter Python queries](https://github.com/nvim-treesitter/nvim-treesitter/blob/main/runtime/queries/python/highlights.scm)
- [tree-sitter-python tags.scm](https://github.com/tree-sitter/tree-sitter-python/blob/main/queries/tags.scm)
- [grep-ast implementation](https://github.com/paul-gauthier/grep-ast)
