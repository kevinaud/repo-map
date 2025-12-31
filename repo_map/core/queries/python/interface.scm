; Python interface query (Verbosity Level 3: INTERFACE)
; Captures definition names + parameters + docstrings
; Output: full signatures with documentation

(module (expression_statement (assignment left: (identifier) @name.definition.constant) @definition.constant))

(class_definition
  name: (identifier) @name.definition.class
  body: (block
    (expression_statement
      (string) @docstring.class)?)) @definition.class

(function_definition
  name: (identifier) @name.definition.function
  parameters: (parameters) @signature.parameters
  return_type: (type)? @signature.return_type
  body: (block
    (expression_statement
      (string) @docstring.function)?)) @definition.function

; Decorated functions/classes
(decorated_definition
  (decorator) @decorator
  definition: (function_definition
    name: (identifier) @name.definition.function
    parameters: (parameters) @signature.parameters
    return_type: (type)? @signature.return_type
    body: (block
      (expression_statement
        (string) @docstring.function)?))) @definition.decorated_function

(decorated_definition
  (decorator) @decorator
  definition: (class_definition
    name: (identifier) @name.definition.class
    body: (block
      (expression_statement
        (string) @docstring.class)?))) @definition.decorated_class
