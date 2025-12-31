"""Helper utility functions."""

import re
from datetime import datetime


def format_timestamp(ts: int) -> str:
  """Format a Unix timestamp as ISO string.

  Args:
      ts: Unix timestamp in seconds.

  Returns:
      ISO formatted datetime string.
  """
  return datetime.fromtimestamp(ts).isoformat()


def validate_email(email: str) -> bool:
  """Validate an email address format.

  Args:
      email: Email address to validate.

  Returns:
      True if valid format, False otherwise.
  """
  pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
  return bool(re.match(pattern, email))


def truncate_string(s: str, max_length: int = 100) -> str:
  """Truncate a string to maximum length.

  Args:
      s: String to truncate.
      max_length: Maximum length (default 100).

  Returns:
      Truncated string with ellipsis if needed.
  """
  if len(s) <= max_length:
    return s
  return s[: max_length - 3] + "..."


# Constants
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
