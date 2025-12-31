; TypeScript structure query (Verbosity Level 2: STRUCTURE)
; Captures only definition names - class, interface, function, type names
; Output: minimal skeleton showing what exists

; Classes
(class_declaration
  name: (type_identifier) @name.definition.class) @definition.class

; Interfaces
(interface_declaration
  name: (type_identifier) @name.definition.interface) @definition.interface

; Type aliases
(type_alias_declaration
  name: (type_identifier) @name.definition.type) @definition.type

; Enums
(enum_declaration
  name: (identifier) @name.definition.enum) @definition.enum

; Functions
(function_declaration
  name: (identifier) @name.definition.function) @definition.function

; Arrow functions assigned to const/let
(lexical_declaration
  (variable_declarator
    name: (identifier) @name.definition.function
    value: (arrow_function))) @definition.function

; Methods
(method_definition
  name: (property_identifier) @name.definition.method) @definition.method

; Exported variables/constants
(export_statement
  declaration: (lexical_declaration
    (variable_declarator
      name: (identifier) @name.definition.constant))) @definition.constant
