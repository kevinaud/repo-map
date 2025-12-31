; Python structure query (Verbosity Level 2: STRUCTURE)
; Captures only definition names - class, function, method, constant names
; Output: minimal skeleton showing what exists

(module (expression_statement (assignment left: (identifier) @name.definition.constant) @definition.constant))

(class_definition
  name: (identifier) @name.definition.class) @definition.class

(function_definition
  name: (identifier) @name.definition.function) @definition.function
