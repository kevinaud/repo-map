; HTML interface query (Verbosity Level 3: INTERFACE)
; Captures structural elements + classes + important attributes
; Output: document structure with styling and behavior hooks

; Document title
(element
  (start_tag
    (tag_name) @tag
    (#eq? @tag "title"))
  (text) @name.definition.title) @definition.title

; Meta tags
(element
  (start_tag
    (tag_name) @tag
    (attribute
      (attribute_name) @attr_name
      (quoted_attribute_value) @meta.value)*
    (#eq? @tag "meta"))) @definition.meta

; Main structural elements with attributes
(element
  (start_tag
    (tag_name) @name.definition.section
    (attribute)* @section.attributes)
  (#match? @name.definition.section "^(html|head|body|main|header|footer|nav|aside|article|section)$")) @definition.section

; Elements with id attribute
(element
  (start_tag
    (tag_name) @element.tag
    (attribute
      (attribute_name) @attr_name
      (quoted_attribute_value
        (attribute_value) @name.definition.id))
    (attribute)* @element.attributes
    (#eq? @attr_name "id"))) @definition.id

; Elements with class attribute (for major components)
(element
  (start_tag
    (tag_name) @element.tag
    (attribute
      (attribute_name) @attr_name
      (quoted_attribute_value
        (attribute_value) @name.definition.class))
    (#eq? @attr_name "class"))) @definition.class

; Heading elements with text
(element
  (start_tag
    (tag_name) @tag
    (attribute)* @heading.attributes
    (#match? @tag "^h[1-6]$"))
  (text)? @name.definition.heading) @definition.heading

; Forms with all attributes
(element
  (start_tag
    (tag_name) @tag
    (attribute)* @form.attributes
    (#eq? @tag "form"))) @definition.form

; Input elements with type and name
(element
  (self_closing_tag
    (tag_name) @tag
    (attribute
      (attribute_name) @attr_name
      (quoted_attribute_value) @input.value)*
    (#eq? @tag "input"))) @definition.input

; Button elements
(element
  (start_tag
    (tag_name) @tag
    (attribute)* @button.attributes
    (#eq? @tag "button"))
  (text)? @name.definition.button) @definition.button

; Script tags with src
(script_element
  (start_tag
    (attribute
      (attribute_name) @attr_name
      (quoted_attribute_value
        (attribute_value) @name.reference.script))
    (#eq? @attr_name "src"))) @reference.script

; Link tags (stylesheets)
(element
  (start_tag
    (tag_name) @tag
    (attribute)* @link.attributes
    (#eq? @tag "link"))) @definition.link

; Img tags with src and alt
(element
  (self_closing_tag
    (tag_name) @tag
    (attribute)* @img.attributes
    (#eq? @tag "img"))) @definition.img
