import json
from typing import Any

from mcp import types
from mcp.shared.metadata_utils import get_display_name

from mcp_client.client_session_provider import get_client_session_by_server
from prompt import PromptHelper
from state import State


def create_mcp_tool_function(state: State, prompt_helper: PromptHelper):
    """Create a call_mcp_tool function with state bound."""

    async def call_mcp_tool(server: str, tool_name: str, args: dict) -> str | dict[str, Any]:
        print(f"Calling MCP tool: {tool_name} on server: {server} with args: {args}")
        async with get_client_session_by_server(server, state.mcp_config) as session:
            # Initialize the connection
            await session.initialize()

            tools = await session.list_tools()
            # Call the tool with collected input
            try:
                full_arguments = await prompt_helper.get_full_args(tools, tool_name, args)

                print(f"Full arguments for tool {tool_name}: {full_arguments}")
                result = await session.call_tool(tool_name, arguments=full_arguments)
                result_unstructured = result.content[0]
                if isinstance(result_unstructured, types.TextContent):
                    # Try to parse the result as JSON
                    if result_unstructured.text.startswith("{") or result_unstructured.text.startswith("["):
                        try:
                            return json.loads(result_unstructured.text)
                        except json.JSONDecodeError:
                            print("Failed to parse result as JSON, returning raw text.")

                    return result_unstructured.text
                else:
                    return ""
            except Exception as e:
                print(f"Error calling tool {tool_name}: {e}")
                print("Available tools:")
                for tool in tools.tools:
                    print(f" - {tool.name}: {get_display_name(tool)}")
                return ""

    return call_mcp_tool
