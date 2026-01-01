import logging
from pathlib import Path

import structlog


def configure_logging() -> None:
  """Configure structlog for normal application logging."""
  structlog.configure(
    processors=[
      structlog.processors.TimeStamper(fmt="iso"),
      structlog.processors.add_log_level,
      structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
  )


def configure_adk_debug_logging(log_file: Path | None = None) -> Path:
  """Configure detailed ADK logging for debugging.

  Enables DEBUG level logging for Google ADK modules and routes
  the verbose output to a file to keep console clean.

  Args:
      log_file: Optional path for log file. Defaults to navigator_debug.log
                in current directory.

  Returns:
      Path to the log file being written
  """
  if log_file is None:
    log_file = Path("navigator_debug.log")

  # Create a file handler for ADK debug logs
  file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
  file_handler.setLevel(logging.DEBUG)
  file_handler.setFormatter(
    logging.Formatter(
      "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
      datefmt="%Y-%m-%d %H:%M:%S",
    )
  )

  # Configure the root logger to capture ADK logs
  # ADK uses loggers named like: google_adk.google.adk.agents.llm_agent
  adk_logger = logging.getLogger("google_adk")
  adk_logger.setLevel(logging.DEBUG)
  adk_logger.addHandler(file_handler)

  # Also capture google.genai logs for API interactions
  genai_logger = logging.getLogger("google_genai")
  genai_logger.setLevel(logging.DEBUG)
  genai_logger.addHandler(file_handler)

  # Capture google.adk logs (alternate naming pattern)
  google_adk_logger = logging.getLogger("google.adk")
  google_adk_logger.setLevel(logging.DEBUG)
  google_adk_logger.addHandler(file_handler)

  return log_file
