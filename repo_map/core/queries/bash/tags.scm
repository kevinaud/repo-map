; Bash tags query (default)
; Captures definitions and references for Bash/shell scripts

; Function definitions
(function_definition
  name: (word) @name.definition.function) @definition.function

; Variable assignments
(variable_assignment
  name: (variable_name) @name.definition.variable) @definition.variable

; Command invocations as references
(command
  name: (command_name) @name.reference.call) @reference.call

; Variable expansions as references
(simple_expansion
  (variable_name) @name.reference.variable) @reference.variable

(expansion
  (variable_name) @name.reference.variable) @reference.variable
