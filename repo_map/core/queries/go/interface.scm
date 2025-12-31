; Go interface query (Verbosity Level 3: INTERFACE)
; Captures definition names + parameters + return types + comments
; Output: full signatures with documentation

(package_clause "package" (package_identifier) @name.definition.module) @definition.module

; Functions with full signature
(
  (comment)* @doc
  .
  (function_declaration
    name: (identifier) @name.definition.function
    parameters: (parameter_list) @signature.parameters
    result: [
      (parameter_list) @signature.return
      (type_identifier) @signature.return
      (pointer_type) @signature.return
      (slice_type) @signature.return
      (map_type) @signature.return
      (channel_type) @signature.return
      (qualified_type) @signature.return
    ]?) @definition.function
)

; Methods with receiver and full signature
(
  (comment)* @doc
  .
  (method_declaration
    receiver: (parameter_list) @signature.receiver
    name: (field_identifier) @name.definition.method
    parameters: (parameter_list) @signature.parameters
    result: [
      (parameter_list) @signature.return
      (type_identifier) @signature.return
      (pointer_type) @signature.return
      (slice_type) @signature.return
      (map_type) @signature.return
      (channel_type) @signature.return
      (qualified_type) @signature.return
    ]?) @definition.method
)

; Struct types with fields
(type_declaration
  (type_spec
    name: (type_identifier) @name.definition.struct
    type: (struct_type
      (field_declaration_list)? @struct.fields))) @definition.struct

; Interface types with methods
(type_declaration
  (type_spec
    name: (type_identifier) @name.definition.interface
    type: (interface_type
      (method_spec_list)? @interface.methods))) @definition.interface

; Type aliases
(type_declaration
  (type_spec
    name: (type_identifier) @name.definition.type
    type: (_) @type.alias)) @definition.type

; Constants with type
(const_declaration
  (const_spec
    name: (identifier) @name.definition.constant
    type: (_)? @constant.type
    value: (_)? @constant.value)) @definition.constant

; Variables with type
(var_declaration
  (var_spec
    name: (identifier) @name.definition.variable
    type: (_)? @variable.type)) @definition.variable
