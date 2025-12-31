; Protocol Buffers structure query (Verbosity Level 2: STRUCTURE)
; Captures only definition names - message, enum, service, rpc names
; Output: minimal skeleton showing what exists

; Package name
(package
  (full_ident) @name.definition.package) @definition.package

; Message definitions
(message
  (message_name) @name.definition.message) @definition.message

; Enum definitions
(enum
  (enum_name) @name.definition.enum) @definition.enum

; Service definitions
(service
  (service_name) @name.definition.service) @definition.service

; RPC method definitions
(rpc
  (rpc_name) @name.definition.rpc) @definition.rpc

; Oneof definitions
(oneof
  (oneof_name) @name.definition.oneof) @definition.oneof
