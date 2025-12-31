; Protocol Buffers interface query (Verbosity Level 3: INTERFACE)
; Captures definition names + fields + types + options
; Output: full signatures with field definitions

; Package with options
(package
  (full_ident) @name.definition.package) @definition.package

; Messages with fields
(message
  (message_name) @name.definition.message
  (message_body
    (field)* @fields
    (oneof)* @oneofs
    (map_field)* @maps)) @definition.message

; Enums with values
(enum
  (enum_name) @name.definition.enum
  (enum_body
    (enum_field)* @values)) @definition.enum

; Enum field values
(enum_field
  (ident) @name.definition.enum_value) @definition.enum_value

; Services with RPC methods
(service
  (service_name) @name.definition.service
  (service_body
    (rpc)* @methods)) @definition.service

; RPC with request/response types
(rpc
  (rpc_name) @name.definition.rpc
  (message_type) @signature.request_type
  (message_type) @signature.response_type) @definition.rpc

; Fields with types and numbers
(field
  (type) @field.type
  (field_name) @name.definition.field
  (field_number) @field.number
  (field_options)? @field.options) @definition.field

; Map fields
(map_field
  (key_type) @map.key_type
  (type) @map.value_type
  (field_name) @name.definition.map_field
  (field_number) @field.number) @definition.map_field

; Oneof fields
(oneof
  (oneof_name) @name.definition.oneof
  (oneof_field)* @oneof.fields) @definition.oneof
