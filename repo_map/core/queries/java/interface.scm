; Java interface query (Verbosity Level 3: INTERFACE)
; Captures definition names + parameters + annotations + javadoc
; Output: full signatures with documentation

; Classes with javadoc
(class_declaration
  (modifiers
    (marker_annotation)? @annotation
    (annotation)? @annotation)*
  name: (identifier) @name.definition.class
  superclass: (superclass)? @extends
  interfaces: (super_interfaces)? @implements) @definition.class

; Interfaces with javadoc
(interface_declaration
  (modifiers
    (marker_annotation)? @annotation
    (annotation)? @annotation)*
  name: (identifier) @name.definition.interface
  (extends_interfaces)? @extends) @definition.interface

; Enums
(enum_declaration
  (modifiers
    (marker_annotation)? @annotation
    (annotation)? @annotation)*
  name: (identifier) @name.definition.enum
  interfaces: (super_interfaces)? @implements) @definition.enum

; Methods with full signature
(method_declaration
  (modifiers
    (marker_annotation)? @annotation
    (annotation)? @annotation)*
  type: (_) @return_type
  name: (identifier) @name.definition.method
  parameters: (formal_parameters) @signature.parameters
  (throws)? @throws) @definition.method

; Constructors with full signature
(constructor_declaration
  (modifiers
    (marker_annotation)? @annotation
    (annotation)? @annotation)*
  name: (identifier) @name.definition.constructor
  parameters: (formal_parameters) @signature.parameters
  (throws)? @throws) @definition.constructor

; Fields with type
(field_declaration
  (modifiers
    (marker_annotation)? @annotation
    (annotation)? @annotation)*
  type: (_) @field_type
  declarator: (variable_declarator
    name: (identifier) @name.definition.field)) @definition.field

; Constants
(constant_declaration
  (modifiers
    (marker_annotation)? @annotation
    (annotation)? @annotation)*
  type: (_) @constant_type
  declarator: (variable_declarator
    name: (identifier) @name.definition.constant)) @definition.constant
