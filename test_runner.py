#!/usr/bin/env python3
"""Test runner script that patches collect_var_value for e2e testing."""
import asyncio
from unittest.mock import patch

from cxk import main


async def mock_collect_var_value(var_name: str) -> str:
    """Mock implementation that returns predictable values based on variable name."""
    mock_values = {
        "name": "John",
        "age": "25",
        "city": "New York",
        "weather": '{"condition": "sunny", "temp": "75F"}',
        "username": "testuser",
        "user": "test_user"
    }
    return mock_values.get(var_name, f"mock_value_{var_name}")


if __name__ == "__main__":
    # Patch collect_var_value before running main
    with patch('commands.create_spec.collect_var_value', side_effect=mock_collect_var_value):
        asyncio.run(main())