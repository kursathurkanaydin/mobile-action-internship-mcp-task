import logging
import logging.handlers
from pathlib import Path

from mcp_task.config import LOG_DIR, LOG_LEVEL

_MAX_BYTES = 5_000_000
_BACKUP_COUNT = 3


def configure_logging(log_dir: Path | None = None, level: str | None = None) -> None:
    """Set up file + stderr logging for this project's own loggers.

    Writes to <log_dir>/mcp_task.log (rotated at 5MB, 3 backups kept) so
    logs survive server restarts and are inspectable regardless of which
    MCP client spawned the server (a client's own log capture, e.g. Claude
    Desktop's, is outside our control) - plus stderr, for live viewing when
    running the server directly or via MCP Inspector. Without this,
    logger.info() calls (e.g. the credit-cost log in clients/mobileaction.py)
    were invisible: Python's default "handler of last resort" only surfaces
    WARNING and above.

    Configures the "mcp_task" logger specifically (every module here uses
    logging.getLogger(__name__), so they're all children of it), NOT the
    root logger - third-party libraries (httpx, redis) log their own INFO
    messages otherwise, and httpx's in particular includes the full request
    URL with the MobileAction API token as a query param, which would
    silently leak into this log file if we turned on INFO globally.

    Idempotent - safe to call more than once (e.g. mcp_instance.py calls it
    at import time, and every test importing a tool module transitively
    re-triggers that): clears any handlers from a previous call first
    instead of stacking duplicates.
    """
    log_dir = log_dir or LOG_DIR
    level = level or LOG_LEVEL
    log_dir.mkdir(parents=True, exist_ok=True)

    mcp_task_logger = logging.getLogger("mcp_task")
    for handler in mcp_task_logger.handlers[:]:
        mcp_task_logger.removeHandler(handler)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "mcp_task.log", maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    mcp_task_logger.setLevel(level)
    mcp_task_logger.addHandler(file_handler)
    mcp_task_logger.addHandler(stream_handler)
