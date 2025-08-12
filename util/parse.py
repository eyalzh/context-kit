import json
from typing import Any


def parse_input_string(value: str) -> str | dict[str, Any]:
    """Parse a string input that may be JSON or a simple string.

    Args:
        value (str): The input string to parse.

    Returns:
        str | dict[str, Any]: Parsed value, either as a string or a dictionary.
    """
    value = value.strip()
    if value.startswith("{") or value.startswith("["):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value
