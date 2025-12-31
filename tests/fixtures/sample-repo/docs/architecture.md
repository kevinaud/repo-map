# Architecture Overview

## System Design

The sample repository follows a layered architecture:

```
┌─────────────────┐
│   Application   │
├─────────────────┤
│    Services     │
├─────────────────┤
│      Core       │
└─────────────────┘
```

## Core Layer

The core layer contains fundamental business logic:

### Authentication

- `UserAuth`: Handles user authentication
- `Token`: Represents session tokens
- `AuthError`: Custom exception for auth failures

### Data Storage

- `DataStore`: In-memory key-value store
- Thread-safe operations
- Simple CRUD interface

## Design Decisions

### Why In-Memory Storage?

For testing purposes, in-memory storage provides:
1. Fast test execution
2. No external dependencies
3. Easy state reset between tests

### Security Considerations

- Tokens should be rotated regularly
- Secret keys should be environment variables
- Password hashing not implemented (demo only)
