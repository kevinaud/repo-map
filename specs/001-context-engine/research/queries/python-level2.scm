; python-level2.scm
; ==================
; Level 2: Structure only - top-level definitions (names only)
;
; Captures class names, function names, and module-level constant assignments.
; Does NOT capture signatures, docstrings, or implementation bodies.
;
; Usage: Run query, collect @name.definition.* captures
; Output: List of definition names with their types

; Module-level constant assignments
(module
  (expression_statement
    (assignment
      left: (identifier) @name.definition.constant)))

; Class definitions - capture name only
(class_definition
  name: (identifier) @name.definition.class)

; Function definitions at module level - capture name only
(function_definition
  name: (identifier) @name.definition.function)

; Also capture method names inside classes for completeness
(class_definition
  body: (block
    (function_definition
      name: (identifier) @name.definition.method)))

; Async function definitions
(function_definition
  "async"
  name: (identifier) @name.definition.async_function)
