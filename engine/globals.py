import logging
from typing import Any

from mcp import types
from mcp.shared.metadata_utils import get_display_name
from pydantic import AnyUrl

from mcp_client import get_client_session_by_server, handle_binary_content
from prompt import PromptHelper
from state import State
from util.parse import parse_input_string


def create_mcp_tool_function(prompt_helper: PromptHelper, state: State):
    """Create a call_mcp_tool function with state bound."""

    async def call_mcp_tool(server: str, tool_name: str, args: dict) -> str | dict[str, Any]:
        logging.info(f"Calling MCP tool: {tool_name} on server: {server} with args: {args}")
        async with get_client_session_by_server(server) as session:
            tools = await session.list_tools()
            try:
                # Collect missing required arguments interactively
                full_arguments = await prompt_helper.get_full_args(tools, tool_name, args)

                logging.debug(f"Full arguments for tool {tool_name}: {full_arguments}")
                result = await session.call_tool(tool_name, arguments=full_arguments)
                result_unstructured = result.content[0]
                if isinstance(result_unstructured, types.TextContent):
                    return parse_input_string(result_unstructured.text)
                elif isinstance(result_unstructured, types.ImageContent | types.AudioContent):
                    if state.config_dir:
                        file_path = handle_binary_content(state.config_dir, result_unstructured)
                        return file_path if file_path else ""
                    else:
                        logging.error("Config directory not available for binary data storage")
                        return ""
                else:
                    return ""
            except Exception as e:
                logging.error(f"Error calling tool {tool_name}: {e}")
                logging.error("Available tools:")
                for tool in tools.tools:
                    logging.error(f" - {tool.name}: {get_display_name(tool)}")
                return ""

    return call_mcp_tool


def create_mcp_resource_function(state: State):
    """Create a get_mcp_resource function with state bound."""

    async def get_mcp_resource(server: str, resource_uri: str) -> str | dict[str, Any]:
        logging.info(f"Getting MCP resource: {resource_uri} in server: {server}")
        async with get_client_session_by_server(server) as session:
            # Fetch the resource (first content item for now)
            try:
                resource = await session.read_resource(AnyUrl(resource_uri))
                result_unstructured = resource.contents[0]
                if isinstance(result_unstructured, types.TextResourceContents):
                    return parse_input_string(result_unstructured.text)
                elif isinstance(result_unstructured, types.BlobResourceContents):
                    if state.config_dir:
                        file_path = handle_binary_content(state.config_dir, result_unstructured)
                        return file_path if file_path else ""
                    else:
                        logging.error("Config directory not available for binary data storage")
                        return ""
                else:
                    logging.debug(f"Resource {resource_uri} returned non-text content")
                    return ""
            except Exception as e:
                logging.error(f"Error fetching resource {resource_uri}: {e}")
                return {}

    return get_mcp_resource
