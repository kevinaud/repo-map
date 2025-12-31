; Protocol Buffers tags query (default)
; Captures definitions and references for .proto files

; Message definitions
(message
  (message_name) @name.definition.message) @definition.message

; Enum definitions
(enum
  (enum_name) @name.definition.enum) @definition.enum

; Service definitions
(service
  (service_name) @name.definition.service) @definition.service

; RPC definitions
(rpc
  (rpc_name) @name.definition.rpc) @definition.rpc

; Field type references
(field
  (type) @name.reference.type) @reference.type

; Message type references in fields
(message_or_enum_type) @name.reference.message @reference.message

; Package declaration
(package
  (full_ident) @name.definition.package) @definition.package
