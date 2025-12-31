; Java structure query (Verbosity Level 2: STRUCTURE)
; Captures only definition names - class, interface, method, field names
; Output: minimal skeleton showing what exists

(class_declaration
  name: (identifier) @name.definition.class) @definition.class

(interface_declaration
  name: (identifier) @name.definition.interface) @definition.interface

(enum_declaration
  name: (identifier) @name.definition.enum) @definition.enum

(method_declaration
  name: (identifier) @name.definition.method) @definition.method

(constructor_declaration
  name: (identifier) @name.definition.constructor) @definition.constructor

(field_declaration
  declarator: (variable_declarator
    name: (identifier) @name.definition.field)) @definition.field

(constant_declaration
  declarator: (variable_declarator
    name: (identifier) @name.definition.constant)) @definition.constant
