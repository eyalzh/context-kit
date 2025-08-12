from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO


@contextmanager
def get_mcp_log_file(config_dir: Path | None) -> Generator[TextIO, None, None]:
    """
    Context manager that provides a log file handle for MCP stderr output.

    Args:
        config_dir: The configuration directory (typically .cxk) where logs should be stored.
                   If None, falls back to current directory.

    Yields:
        TextIO: File handle for writing MCP stderr logs
    """
    if config_dir is None:
        log_dir = Path.cwd() / ".cxk"
    else:
        log_dir = config_dir

    # Ensure log directory exists
    log_dir.mkdir(exist_ok=True)

    # Set up log file path
    log_file_path = log_dir / "mcp.log"

    # Open log file for stderr output
    with open(log_file_path, "a", encoding="utf-8") as errlog:
        yield errlog
