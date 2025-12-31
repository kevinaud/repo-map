; Markdown interface query (Verbosity Level 3: INTERFACE)
; Captures headings + first paragraph (summary) under each heading
; Output: document outline with brief descriptions

(atx_heading
  (atx_h1_marker)
  heading_content: (inline) @name.definition.heading1) @definition.heading

(atx_heading
  (atx_h2_marker)
  heading_content: (inline) @name.definition.heading2) @definition.heading

(atx_heading
  (atx_h3_marker)
  heading_content: (inline) @name.definition.heading3) @definition.heading

(atx_heading
  (atx_h4_marker)
  heading_content: (inline) @name.definition.heading4) @definition.heading

(atx_heading
  (atx_h5_marker)
  heading_content: (inline) @name.definition.heading5) @definition.heading

(atx_heading
  (atx_h6_marker)
  heading_content: (inline) @name.definition.heading6) @definition.heading

; Capture paragraphs for context
(paragraph) @content.paragraph

; Capture code blocks for interface documentation
(fenced_code_block
  (info_string)? @content.code_language
  (code_fence_content) @content.code_block) @definition.code_block

; Capture list items for structured content
(list_item) @content.list_item
