; Bash interface query (Verbosity Level 3: INTERFACE)
; Captures definition names + comments + function bodies structure
; Output: function signatures with documentation comments

; Functions with preceding comments
(
  (comment)* @doc
  .
  (function_definition
    name: (word) @name.definition.function
    body: (compound_statement)? @body) @definition.function
)

; Global variable assignments with comments
(
  (comment)* @doc
  .
  (variable_assignment
    name: (variable_name) @name.definition.variable
    value: (_)? @value) @definition.variable
)

; Exported variables
(declaration_command
  (variable_assignment
    name: (variable_name) @name.definition.export
    value: (_)? @value)) @definition.export

; Array declarations
(variable_assignment
  name: (variable_name) @name.definition.array
  value: (array)) @definition.array

; Associative array declarations
(declaration_command
  "-A"
  (variable_assignment
    name: (variable_name) @name.definition.assoc_array)) @definition.assoc_array

; Readonly variables with values
(declaration_command
  "readonly"
  (variable_assignment
    name: (variable_name) @name.definition.readonly
    value: (_)? @value)) @definition.readonly

; Subshell function definitions (alternative syntax)
(
  (comment)* @doc
  .
  (function_definition
    name: (word) @name.definition.function
    body: (subshell)? @body) @definition.function_subshell
)
