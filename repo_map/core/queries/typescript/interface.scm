; TypeScript interface query (Verbosity Level 3: INTERFACE)
; Captures definition names + parameters + types + jsdoc
; Output: full signatures with documentation

; Classes with heritage and decorators
(class_declaration
  (decorator)* @decorator
  name: (type_identifier) @name.definition.class
  (class_heritage)? @extends
  body: (class_body)? @body) @definition.class

; Interfaces with full signature
(interface_declaration
  name: (type_identifier) @name.definition.interface
  (extends_type_clause)? @extends
  body: (interface_body) @body) @definition.interface

; Type aliases with definition
(type_alias_declaration
  name: (type_identifier) @name.definition.type
  value: (_) @type.value) @definition.type

; Enums with members
(enum_declaration
  name: (identifier) @name.definition.enum
  body: (enum_body) @body) @definition.enum

; Functions with full signature
(function_declaration
  name: (identifier) @name.definition.function
  (type_parameters)? @signature.type_params
  parameters: (formal_parameters) @signature.parameters
  return_type: (type_annotation)? @signature.return_type) @definition.function

; Arrow functions with type annotations
(lexical_declaration
  (variable_declarator
    name: (identifier) @name.definition.function
    type: (type_annotation)? @signature.type
    value: (arrow_function
      (type_parameters)? @signature.type_params
      parameters: (formal_parameters) @signature.parameters
      return_type: (type_annotation)? @signature.return_type))) @definition.function

; Methods with full signature
(method_definition
  (accessibility_modifier)? @modifier
  name: (property_identifier) @name.definition.method
  (type_parameters)? @signature.type_params
  parameters: (formal_parameters) @signature.parameters
  return_type: (type_annotation)? @signature.return_type) @definition.method

; Property signatures in interfaces
(property_signature
  name: (property_identifier) @name.definition.property
  type: (type_annotation) @property.type) @definition.property

; Method signatures in interfaces
(method_signature
  name: (property_identifier) @name.definition.method
  (type_parameters)? @signature.type_params
  parameters: (formal_parameters) @signature.parameters
  return_type: (type_annotation)? @signature.return_type) @definition.method_signature

; Exported constants
(export_statement
  declaration: (lexical_declaration
    (variable_declarator
      name: (identifier) @name.definition.constant
      type: (type_annotation)? @constant.type))) @definition.constant
