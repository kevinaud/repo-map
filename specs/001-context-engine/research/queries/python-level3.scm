; python-level3.scm
; ==================
; Level 3: Interface - signatures and docstrings (no implementation)
;
; Strategy: Capture individual components that together form the interface.
; Post-processing code should combine these captures into coherent output.
;
; Capture groups:
;   @definition.*     - The container node (for position/context)
;   @name.*           - The identifier name
;   @signature.*      - Signature components (params, return type)
;   @docstring.*      - Documentation strings
;   @decorator        - Decorator nodes

; ============================================================
; DECORATORS
; ============================================================

; Capture decorators on functions
(decorated_definition
  (decorator) @decorator
  definition: (function_definition))

; Capture decorators on classes
(decorated_definition
  (decorator) @decorator
  definition: (class_definition))


; ============================================================
; FUNCTION DEFINITIONS
; ============================================================

; Function definition container (for position tracking)
(function_definition) @definition.function

; Function name
(function_definition
  name: (identifier) @name.function)

; Function parameters (full parameters node includes all args, types, defaults)
(function_definition
  parameters: (parameters) @signature.function.parameters)

; Function return type annotation
(function_definition
  return_type: (type) @signature.function.return_type)

; Function docstring - first string expression in the body
; The `.` anchor ensures this only matches the FIRST child
(function_definition
  body: (block
    .
    (expression_statement
      (string) @docstring.function)))

; Async function marker (for reconstruction)
(function_definition
  "async" @modifier.async)


; ============================================================
; CLASS DEFINITIONS
; ============================================================

; Class definition container
(class_definition) @definition.class

; Class name
(class_definition
  name: (identifier) @name.class)

; Class type parameters (generics)
(class_definition
  type_parameters: (type_parameter) @signature.class.type_parameters)

; Class superclasses / bases
(class_definition
  superclasses: (argument_list) @signature.class.superclasses)

; Class docstring - first string expression in the body
(class_definition
  body: (block
    .
    (expression_statement
      (string) @docstring.class)))


; ============================================================
; METHOD DEFINITIONS (functions inside classes)
; ============================================================

; Methods are function_definitions inside class bodies
; We capture them similarly but with context

; Method definition container (function inside class)
(class_definition
  body: (block
    (function_definition) @definition.method))

; Method name
(class_definition
  body: (block
    (function_definition
      name: (identifier) @name.method)))

; Method parameters
(class_definition
  body: (block
    (function_definition
      parameters: (parameters) @signature.method.parameters)))

; Method return type
(class_definition
  body: (block
    (function_definition
      return_type: (type) @signature.method.return_type)))

; Method docstring
(class_definition
  body: (block
    (function_definition
      body: (block
        .
        (expression_statement
          (string) @docstring.method)))))


; ============================================================
; CLASS ATTRIBUTES (typed class variables)
; ============================================================

; Typed class attribute (e.g., `name: str` in dataclass)
(class_definition
  body: (block
    (expression_statement
      (assignment
        left: (identifier) @name.class_attribute
        type: (type) @signature.class_attribute.type))))

; Class attribute with annotation only (no default)
; This captures things like: name: str
(class_definition
  body: (block
    (type
      (identifier) @name.class_attribute.annotated)))


; ============================================================
; MODULE-LEVEL ASSIGNMENTS
; ============================================================

; Module-level typed assignments
(module
  (expression_statement
    (assignment
      left: (identifier) @name.constant
      type: (type)? @signature.constant.type)))

; TypeVar and NewType definitions (special constants)
(module
  (expression_statement
    (assignment
      left: (identifier) @name.type_alias
      right: (call
        function: (identifier) @_func)))
  (#any-of? @_func "TypeVar" "NewType"))
