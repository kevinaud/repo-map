; Markdown structure query (Verbosity Level 2: STRUCTURE)
; Captures only headings - document outline
; Output: minimal skeleton showing section structure

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
