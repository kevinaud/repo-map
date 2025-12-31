; markdown-level3.scm
; ====================
; Level 3: Interface - headings with first paragraph (summaries)
;
; Captures headings PLUS the first paragraph after each heading.
; This provides a document summary/overview level.
;
; Strategy:
; If the grammar provides `section` nodes, we can use them to group
; content with headings. Otherwise, we capture all headings and paragraphs
; and let post-processing match them by position.
;
; This query assumes MDeiml's tree-sitter-markdown which HAS section nodes.


; ============================================================
; HEADINGS (same as level 2)
; ============================================================

(atx_heading
  [(atx_h1_marker) (atx_h2_marker) (atx_h3_marker)
   (atx_h4_marker) (atx_h5_marker) (atx_h6_marker)]
  (inline) @content.heading) @definition.heading

(setext_heading
  (paragraph
    (inline) @content.heading)) @definition.heading


; ============================================================
; SECTION CONTENT (first paragraph)
; ============================================================

; First paragraph directly after an ATX heading
; The `.` anchor means "immediately following sibling"
(section
  (atx_heading) @context.heading
  .
  (paragraph) @content.first_paragraph)

; First paragraph directly after a Setext heading
(section
  (setext_heading) @context.heading
  .
  (paragraph) @content.first_paragraph)


; ============================================================
; ALTERNATIVE: If section nodes don't exist
; ============================================================
; Uncomment these if your markdown parser doesn't have section grouping.
; Then handle heading-paragraph association in post-processing code.

; (atx_heading) @heading
; (setext_heading) @heading
; (paragraph) @paragraph


; ============================================================
; ADDITIONAL STRUCTURAL ELEMENTS (optional)
; ============================================================

; Capture top-level list items (bullet points at section level)
; This helps understand document structure
(section
  (atx_heading) @context.heading
  .
  (list) @content.first_list)

; Capture code blocks following headings
; Useful for API documentation patterns
(section
  (atx_heading) @context.heading
  .
  (fenced_code_block
    (info_string
      (language) @meta.code_language)?
    (code_fence_content) @content.code_example))


; ============================================================
; LINK REFERENCES (useful for documentation)
; ============================================================

; Link definitions at the bottom of documents
(link_reference_definition
  (link_label) @name.link_label
  (link_destination) @content.link_url)


; ============================================================
; FRONT MATTER (if supported by parser)
; ============================================================

; YAML front matter (common in static site generators)
; Note: This depends on the parser supporting front matter
; (minus_metadata) @content.frontmatter
