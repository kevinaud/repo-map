"""Tests for authentication module."""

import pytest
from src.core.auth import AuthError, Token, UserAuth


class TestUserAuth:
  """Test suite for UserAuth class."""

  def test_authenticate_success(self):
    """Test successful authentication."""
    auth = UserAuth()
    token = auth.authenticate("user", "password")
    assert isinstance(token, Token)
    assert token.user_id == "user"

  def test_authenticate_empty_username(self):
    """Test authentication with empty username."""
    auth = UserAuth()
    with pytest.raises(AuthError):
      auth.authenticate("", "password")

  def test_validate_token(self):
    """Test token validation."""
    auth = UserAuth()
    token = auth.authenticate("user", "password")
    assert auth.validate_token(token) is True

  def test_logout(self):
    """Test logout invalidates token."""
    auth = UserAuth()
    token = auth.authenticate("user", "password")
    assert auth.logout(token) is True
    assert auth.validate_token(token) is False
