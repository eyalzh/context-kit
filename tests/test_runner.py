#!/usr/bin/env python3
"""Test runner script that patches collect_var_value for e2e testing."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path so we can import cxk
sys.path.insert(0, str(Path(__file__).parent.parent))

from cxk import main


async def mock_collect_var_value(var_name: str) -> str:
    """Mock implementation that returns predictable values based on variable name."""
    mock_values = {
        "name": "John",
        "age": "25",
        "city": "New York",
        "weather": '{"condition": "sunny", "temp": "75F"}',
        "username": "testuser",
        "user": "test_user",
    }
    return mock_values.get(var_name, f"mock_value_{var_name}")


async def mock_collect_var_value_interactive(var_name: str) -> str:
    """Mock implementation for interactive variable collection that returns predictable values."""
    # In test mode, always use direct value (same as mock_collect_var_value)
    return await mock_collect_var_value(var_name)


async def mock_collect_tool_input(input_schema, existing_args=None, include_optional=True):
    """Mock implementation for collecting MCP tool input parameters."""
    if existing_args is None:
        existing_args = {}

    properties = input_schema["properties"]
    required = input_schema.get("required", [])
    values = existing_args.copy()

    # Mock values for common MCP tool parameters
    mock_tool_values = {
        "ticketId": "mock_value_ticketId",
        "b": 10,  # For integer type parameters like 'b' in add function
        "cloudId": "mock_cloudId",
    }

    for field_name, field_info in properties.items():
        # Skip if field is already provided in existing_args
        if field_name in existing_args:
            continue

        is_required = field_name in required
        field_type = field_info.get("type", "string")

        if not include_optional and not is_required:
            continue

        # Provide mock value based on field type and name
        if field_name in mock_tool_values:
            values[field_name] = mock_tool_values[field_name]
        elif field_type == "integer":
            values[field_name] = 42
        elif field_type == "boolean":
            values[field_name] = True
        else:  # string or other types
            values[field_name] = f"mock_value_{field_name}"

    return values


if __name__ == "__main__":
    with (
        patch("prompt.PromptHelper.collect_var_value", side_effect=mock_collect_var_value),
        patch("prompt.PromptHelper.collect_var_value_interactive", side_effect=mock_collect_var_value_interactive),
        patch("prompt.PromptHelper.collect_tool_input", side_effect=mock_collect_tool_input),
    ):
        asyncio.run(main())
