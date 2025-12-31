; Markdown headings as definitions
; H1 headings
(atx_heading
  (atx_h1_marker)
  (inline) @name.definition.heading) @definition.heading

; H2 headings  
(atx_heading
  (atx_h2_marker)
  (inline) @name.definition.heading) @definition.heading

; H3 headings
(atx_heading
  (atx_h3_marker)
  (inline) @name.definition.heading) @definition.heading

; H4 headings
(atx_heading
  (atx_h4_marker)
  (inline) @name.definition.heading) @definition.heading

; H5 headings
(atx_heading
  (atx_h5_marker)
  (inline) @name.definition.heading) @definition.heading

; H6 headings
(atx_heading
  (atx_h6_marker)
  (inline) @name.definition.heading) @definition.heading

; Setext headings (underlined with === or ---)
(setext_heading
  (paragraph
    (inline) @name.definition.heading)) @definition.heading

; Code block language identifiers as references
(fenced_code_block
  (info_string
    (language) @name.reference.language)) @reference.language
