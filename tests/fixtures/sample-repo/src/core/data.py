"""Data storage module."""

from collections.abc import Iterator
from typing import Any


class DataStore:
  """Simple in-memory data store.

  Provides basic CRUD operations for testing purposes.
  """

  def __init__(self):
    """Initialize empty data store."""
    self._data: dict[str, Any] = {}

  def get(self, key: str) -> Any | None:
    """Retrieve a value by key.

    Args:
        key: The key to look up.

    Returns:
        The stored value or None if not found.
    """
    return self._data.get(key)

  def set(self, key: str, value: Any) -> None:
    """Store a value.

    Args:
        key: The key to store under.
        value: The value to store.
    """
    self._data[key] = value

  def delete(self, key: str) -> bool:
    """Delete a value by key.

    Args:
        key: The key to delete.

    Returns:
        True if deleted, False if key didn't exist.
    """
    if key in self._data:
      del self._data[key]
      return True
    return False

  def keys(self) -> Iterator[str]:
    """Iterate over all keys.

    Yields:
        Each key in the store.
    """
    yield from self._data.keys()

  def clear(self) -> int:
    """Remove all data.

    Returns:
        Number of items cleared.
    """
    count = len(self._data)
    self._data.clear()
    return count
