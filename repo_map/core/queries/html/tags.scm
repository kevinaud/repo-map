; HTML tags query (default)
; Captures definitions and references for HTML files

; Elements with id attribute as definitions
(element
  (start_tag
    (tag_name) @tag
    (attribute
      (attribute_name) @attr_name
      (quoted_attribute_value) @name.definition.id)
    (#eq? @attr_name "id"))) @definition.element

; Script tags as references
(script_element
  (start_tag
    (attribute
      (attribute_name) @attr_name
      (quoted_attribute_value) @name.reference.script)
    (#eq? @attr_name "src"))) @reference.script

; Link tags as references  
(element
  (start_tag
    (tag_name) @tag
    (attribute
      (attribute_name) @attr_name
      (quoted_attribute_value) @name.reference.stylesheet)
    (#eq? @tag "link")
    (#eq? @attr_name "href"))) @reference.stylesheet

; Anchor hrefs as references
(element
  (start_tag
    (tag_name) @tag
    (attribute
      (attribute_name) @attr_name
      (quoted_attribute_value) @name.reference.link)
    (#eq? @tag "a")
    (#eq? @attr_name "href"))) @reference.link
