"""Authentication module for user management."""

from dataclasses import dataclass


@dataclass
class Token:
  """Represents an authentication token."""

  value: str
  expires_at: int
  user_id: str


class AuthError(Exception):
  """Raised when authentication fails."""

  pass


class UserAuth:
  """Handles user authentication and session management.

  This class provides methods for authenticating users,
  validating tokens, and managing sessions.
  """

  def __init__(self, secret_key: str = "default-secret"):
    """Initialize the authentication handler.

    Args:
        secret_key: Secret key for token generation.
    """
    self._secret_key = secret_key
    self._sessions: dict[str, Token] = {}

  def authenticate(self, username: str, password: str) -> Token:
    """Authenticate user and return session token.

    Args:
        username: The user's username.
        password: The user's password.

    Returns:
        A Token object for the authenticated session.

    Raises:
        AuthError: If credentials are invalid.
    """
    # Simplified auth logic for testing
    if not username or not password:
      raise AuthError("Invalid credentials")

    token = Token(
      value=f"token_{username}_{self._secret_key}",
      expires_at=9999999999,
      user_id=username,
    )
    self._sessions[token.value] = token
    return token

  def validate_token(self, token: Token) -> bool:
    """Validate an existing token.

    Args:
        token: The token to validate.

    Returns:
        True if valid, False otherwise.
    """
    return token.value in self._sessions

  def refresh_session(self, token: Token) -> Token | None:
    """Refresh an existing session token.

    Args:
        token: The current token to refresh.

    Returns:
        A new Token if successful, None otherwise.
    """
    if not self.validate_token(token):
      return None

    new_token = Token(
      value=f"{token.value}_refreshed",
      expires_at=token.expires_at + 3600,
      user_id=token.user_id,
    )
    del self._sessions[token.value]
    self._sessions[new_token.value] = new_token
    return new_token

  def logout(self, token: Token) -> bool:
    """End a user session.

    Args:
        token: The session token to invalidate.

    Returns:
        True if session was ended, False if token was invalid.
    """
    if token.value in self._sessions:
      del self._sessions[token.value]
      return True
    return False
