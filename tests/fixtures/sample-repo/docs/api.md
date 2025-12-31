# API Reference

This document provides detailed API documentation for the sample repository.

## Authentication Module

The authentication module handles user login and session management.

### UserAuth Class

Main class for handling authentication.

#### Methods

##### authenticate(username, password)

Authenticates a user with credentials.

**Parameters:**
- `username` (str): The user's username
- `password` (str): The user's password

**Returns:** Token object

**Example:**
```python
auth = UserAuth()
token = auth.authenticate("user@example.com", "secret123")
```

##### validate_token(token)

Validates an existing session token.

**Parameters:**
- `token` (Token): Token to validate

**Returns:** Boolean indicating validity

### Token Class

Represents an authentication token.

**Attributes:**
- `value`: The token string
- `expires_at`: Expiration timestamp
- `user_id`: Associated user ID

## Data Module

The data module provides storage capabilities.

### DataStore Class

Simple key-value storage.

#### Methods

##### get(key)

Retrieves a value by key.

##### set(key, value)

Stores a value under a key.

##### delete(key)

Removes a key-value pair.

## Utilities

### Helper Functions

#### format_timestamp(ts)

Formats Unix timestamp as ISO string.

#### validate_email(email)

Validates email address format.
