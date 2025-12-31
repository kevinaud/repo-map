; markdown-level2.scm
; ====================
; Level 2: Structure only - document outline (headings only)
;
; Captures all heading levels for building a table of contents.
; Does NOT capture paragraph content or other elements.
;
; Note: Uses tree-sitter-markdown from MDeiml which is the most common.
; The inline node contains the actual heading text.

; ATX-style headings (# ## ### etc.)

(atx_heading
  (atx_h1_marker)
  (inline) @name.definition.heading.h1) @definition.heading.h1

(atx_heading
  (atx_h2_marker)
  (inline) @name.definition.heading.h2) @definition.heading.h2

(atx_heading
  (atx_h3_marker)
  (inline) @name.definition.heading.h3) @definition.heading.h3

(atx_heading
  (atx_h4_marker)
  (inline) @name.definition.heading.h4) @definition.heading.h4

(atx_heading
  (atx_h5_marker)
  (inline) @name.definition.heading.h5) @definition.heading.h5

(atx_heading
  (atx_h6_marker)
  (inline) @name.definition.heading.h6) @definition.heading.h6


; Setext-style headings (underlined with === or ---)
; These only support h1 and h2 levels

(setext_heading
  (paragraph
    (inline) @name.definition.heading.setext)) @definition.heading.setext


; Code block language identifiers (useful for structure)
; Shows what languages are used in the document

(fenced_code_block
  (info_string
    (language) @name.reference.code_language)) @reference.code_block
