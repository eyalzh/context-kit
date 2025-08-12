"""
FastMCP reference MCP server for testing and demonstration purposes.
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Test-Server", "1.0.0")


# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


@mcp.tool()
def jsonTest(cloudId: str, ticketId: str, optional_other: str | None = None) -> dict[str, Any]:
    """Mock JOSN test tool"""
    return {
        "id": f"{cloudId} - {ticketId}",
        "summary": f"Summary for {ticketId}",
        "description": "This is a mock Jira ticket description.",
    }


# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"
