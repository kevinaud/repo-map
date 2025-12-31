; HTML structure query (Verbosity Level 2: STRUCTURE)
; Captures only major structural elements - semantic sections and ids
; Output: minimal skeleton showing document structure

; Document title
(element
  (start_tag
    (tag_name) @tag
    (#eq? @tag "title"))
  (text) @name.definition.title) @definition.title

; Main structural elements
(element
  (start_tag
    (tag_name) @name.definition.section)
  (#match? @name.definition.section "^(html|head|body|main|header|footer|nav|aside|article|section)$")) @definition.section

; Elements with id attribute
(element
  (start_tag
    (attribute
      (attribute_name) @attr_name
      (quoted_attribute_value
        (attribute_value) @name.definition.id))
    (#eq? @attr_name "id"))) @definition.id

; Heading elements
(element
  (start_tag
    (tag_name) @tag
    (#match? @tag "^h[1-6]$"))
  (text)? @name.definition.heading) @definition.heading

; Form elements with name
(element
  (start_tag
    (tag_name) @tag
    (attribute
      (attribute_name) @attr_name
      (quoted_attribute_value
        (attribute_value) @name.definition.form))
    (#eq? @tag "form")
    (#match? @attr_name "^(id|name)$"))) @definition.form
