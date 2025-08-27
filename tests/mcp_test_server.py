"""
FastMCP reference MCP server for testing and demonstration purposes.
"""

from typing import Any

import mcp.types as types
from mcp.server.fastmcp import FastMCP, Image
from pydantic import BaseModel, Field

# Create an MCP server
mcp = FastMCP("Test-Server", "1.0.0")


# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


@mcp.tool()
def jsonTest(cloudId: str, ticketId: str, optional_other: str | None = None) -> dict[str, Any]:
    """Mock JSON test tool"""
    return {
        "id": f"{cloudId} - {ticketId}",
        "summary": f"Summary for {ticketId}",
        "description": "This is a mock Jira ticket description.",
    }

# Multi-content response tool
@mcp.tool()
def multi_content_response() -> list[types.TextContent]:
    return [
        types.TextContent(type="text", text="Content 1"),
        types.TextContent(type="text", text="Content 2"),
    ]


# Rich structured data
class WeatherData(BaseModel):
    """Weather information structure."""

    temperature: float = Field(description="Temperature in Celsius")
    humidity: float = Field(description="Humidity percentage")
    condition: str
    wind_speed: float


@mcp.tool()
def get_weather(city: str) -> WeatherData:
    """Get weather for a city - returns structured data."""
    # Simulated weather data
    return WeatherData(
        temperature=72.5,
        humidity=45.0,
        condition="sunny",
        wind_speed=5.2,
    )


# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"


# Add a binary tool (tests/files/image1.avif)
@mcp.tool()
def get_blob() -> Image:
    """Get a binary blob test tool"""
    with open("tests/files/image1.avif", "rb") as f:
        return Image(data=f.read(), format="avif")
