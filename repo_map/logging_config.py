import structlog


def configure_logging():
  structlog.configure(
    processors=[
      structlog.processors.TimeStamper(fmt="iso"),
      structlog.processors.add_log_level,
      structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
  )
