; Bash structure query (Verbosity Level 2: STRUCTURE)
; Captures only definition names - function and variable names
; Output: minimal skeleton showing what exists

; Function definitions
(function_definition
  name: (word) @name.definition.function) @definition.function

; Global variable assignments at top level
(variable_assignment
  name: (variable_name) @name.definition.variable) @definition.variable

; Exported variables
(declaration_command
  (variable_assignment
    name: (variable_name) @name.definition.export)) @definition.export

; Local variables (in functions)
(declaration_command
  "local"
  (variable_assignment
    name: (variable_name) @name.definition.local)) @definition.local

; Readonly variables
(declaration_command
  "readonly"
  (variable_assignment
    name: (variable_name) @name.definition.readonly)) @definition.readonly
