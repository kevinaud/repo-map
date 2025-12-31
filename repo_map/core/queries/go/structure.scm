; Go structure query (Verbosity Level 2: STRUCTURE)
; Captures only definition names - function, method, type, const, var names
; Output: minimal skeleton showing what exists

(package_clause "package" (package_identifier) @name.definition.module) @definition.module

(function_declaration
  name: (identifier) @name.definition.function) @definition.function

(method_declaration
  name: (field_identifier) @name.definition.method) @definition.method

(type_declaration
  (type_spec
    name: (type_identifier) @name.definition.type)) @definition.type

(const_declaration
  (const_spec
    name: (identifier) @name.definition.constant)) @definition.constant

(var_declaration
  (var_spec
    name: (identifier) @name.definition.variable)) @definition.variable
