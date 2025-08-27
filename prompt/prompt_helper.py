import logging

import questionary
from mcp import types

from mcp_client import get_session_manager, handle_binary_content
from state import State


class PromptHelper:
    def __init__(
        self,
        state: State,
    ):
        self._state = state

    async def collect_var_value(self, var_name: str) -> str:
        """Collect a value for a variable using questionary."""

        return await questionary.text(f"Please provide a value for '{var_name}':").ask_async()

    async def get_full_args(self, tools, tool_name, args, include_optional=False):
        """
        Get full arguments for the tool call, using collect_tool_input() to collect missing required fields.

        :param tools: List of available tools
        :param tool_name: Name of the tool to call
        :param args: Arguments provided by the user
        :param include_optional: Whether to include optional parameters in interactive collection
        :return: Full arguments including defaults and required fields
        """
        selected_tool = next((t for t in tools.tools if t.name == tool_name), None)
        if not selected_tool:
            raise ValueError(f"Tool '{tool_name}' not found.")

        input_schema = selected_tool.inputSchema
        if not input_schema:
            return args

        # Use collect_tool_input to fill in missing fields
        full_args = await self.collect_tool_input(input_schema, args, include_optional=include_optional)

        return full_args

    async def collect_tool_input(self, input_schema, existing_args=None, include_optional=True):
        """
        Collect user input based on a schema using Questionary.
        Skip fields that are already provided in existing_args.

        Args:
            input_schema (dict): Schema with 'properties' and 'required' keys
            existing_args (dict, optional): Already collected values

        Returns:
            dict: Dictionary with field names as keys and collected values

        Example:
            schema = {
                'properties': {
                    'a': {'title': 'A', 'type': 'integer'},
                    'b': {'title': 'B', 'type': 'integer'}
                },
                'required': ['a', 'b']
            }
            result = collect_input(schema)  # Returns something like {"a": 5, "b": 3}
        """
        properties = input_schema["properties"]
        required = input_schema.get("required", [])

        if existing_args is None:
            existing_args = {}

        values = existing_args.copy()

        for field_name, field_info in properties.items():
            # Skip if field is already provided in existing_args
            if field_name in existing_args:
                continue

            logging.info(f"Collecting input for field: {field_info}")
            title = field_info["title"] if "title" in field_info else field_name
            field_type = field_info["type"] if "type" in field_info else "string"
            field_desc = field_info.get("description", None)
            is_required = field_name in required
            logging.debug(f"Field '{field_name}': type={field_type}, required={is_required}, desc={field_desc}")

            if not include_optional and not is_required:
                # Skip optional fields if not requested
                continue

            # Create prompt text
            prompt_text = title
            if is_required:
                prompt_text += " (required)"
            else:
                prompt_text += " (optional)"
            prompt_text += ":"

            if field_type == "integer" or field_type == "number":
                # Create validator for integer fields
                def make_integer_validator(required):
                    def validate_integer(value):
                        # Allow empty for optional fields
                        if not value.strip():
                            if required:
                                return "This field is required"
                            return True
                        # Validate integer format
                        try:
                            int(value)
                            return True
                        except ValueError:
                            return "Please enter a valid integer"

                    return validate_integer

                result = await questionary.text(prompt_text, validate=make_integer_validator(is_required)).ask_async()

                # Process the result
                if result and result.strip():
                    values[field_name] = int(result)
                elif is_required:
                    # This shouldn't happen due to validation
                    raise ValueError(f"Required field {field_name} is missing")
                # Optional fields that are empty are not included in output

            elif field_type == "string":
                # Create validator for string fields
                def make_string_validator(required):
                    def validate_string(value):
                        if not value.strip() and required:
                            return "This field is required"
                        return True

                    return validate_string

                result = await questionary.text(
                    prompt_text,
                    validate=make_string_validator(is_required),
                    instruction=field_desc,
                ).ask_async()

                # Process the result
                if result and result.strip():
                    values[field_name] = result
                elif is_required:
                    # This shouldn't happen due to validation
                    raise ValueError(f"Required field {field_name} is missing")
                # Optional fields that are empty are not included in output

            elif field_type == "boolean":
                # Create a yes/no prompt for boolean fields
                result = await questionary.confirm(prompt_text, default=False, qmark="?").ask_async()

                # Store the boolean value
                values[field_name] = result

        return values

    async def collect_var_value_interactive(self, var_name: str) -> str:
        """
        Interactive variable collection - user chooses between direct value or MCP tool.

        :param var_name: Name of the variable to collect
        :return: String value for the variable
        """
        # Ask user to choose between direct value or MCP tool
        choice = await questionary.select(
            f"How would you like to provide the value for '{var_name}'?",
            choices=[
                questionary.Choice("Provide value directly", "direct"),
                questionary.Choice("Use MCP tool to fetch value", "mcp"),
            ],
        ).ask_async()

        if choice == "direct":
            return await self.collect_var_value(var_name)
        elif choice == "mcp":
            return await self._collect_var_value_from_mcp(var_name)
        else:
            raise ValueError("Invalid choice")

    async def _collect_var_value_from_mcp(self, var_name: str) -> str:
        """
        Collect variable value by calling an MCP tool.

        :param var_name: Name of the variable to collect
        :return: String value from MCP tool result
        """
        session_manager = get_session_manager()

        # Select MCP server
        server_name = await self._select_mcp_server()
        if not server_name:
            raise ValueError("No MCP server selected")

        # Get session for selected server (initialize on-demand)
        session = await session_manager.get_session_async(server_name)

        # List available tools
        tools_result = await session.list_tools()
        if not tools_result.tools:
            raise ValueError(f"No tools available on server '{server_name}'")

        # Select tool
        tool_name = await self._select_mcp_tool(tools_result.tools)
        if not tool_name:
            raise ValueError("No tool selected")

        # Get tool arguments (include optional parameters in interactive mode)
        tool_args = await self.get_full_args(tools_result, tool_name, {}, include_optional=True)

        # Call the tool
        logging.info(f"Calling tool '{tool_name}' on server '{server_name}' with args: {tool_args}")
        result = await session.call_tool(tool_name, tool_args)

        if result.isError:
            raise ValueError(f"Tool call failed: {result.content}")

        # Extract content from tool result
        if hasattr(result.content, "__iter__") and not isinstance(result.content, str):
            # Handle list of content items
            content_parts = []
            for item in result.content:
                # Handle binary content types
                if isinstance(item, types.ImageContent | types.AudioContent):
                    if self._state.config_dir:
                        file_path = handle_binary_content(self._state.config_dir, item)
                        if file_path:
                            content_parts.append(file_path)
                        else:
                            logging.error(f"Failed to save binary content for variable '{var_name}'")
                    else:
                        logging.error("Config directory not available for binary data storage")
                # Handle text content
                elif isinstance(item, types.TextContent):
                    content_parts.append(str(item.text))
                # For other content types, convert to string
                else:
                    content_parts.append(str(item))
            content = "\n".join(content_parts)
        else:
            content = str(result.content)

        logging.info(f"Tool result for '{var_name}': {content}")
        return content

    async def _select_mcp_server(self) -> str | None:
        """
        Present user with list of available MCP servers to choose from.

        :return: Selected server name or None if no servers available
        """
        session_manager = get_session_manager()
        server_names = session_manager.server_names

        if not server_names:
            logging.error("No MCP servers available")
            return None

        if len(server_names) == 1:
            logging.info(f"Using the only available MCP server: {server_names[0]}")
            return server_names[0]

        # Let user choose from available servers
        server_name = await questionary.select("Select an MCP server:", choices=server_names).ask_async()

        return server_name

    async def _select_mcp_tool(self, tools) -> str | None:
        """
        Present user with list of available tools to choose from.

        :param tools: List of tool objects from MCP server
        :return: Selected tool name or None if no tools available
        """
        if not tools:
            logging.error("No tools available")
            return None

        if len(tools) == 1:
            logging.info(f"Using the only available tool: {tools[0].name}")
            return tools[0].name

        # Create choices with tool name and description
        choices = []
        for tool in tools:
            description = tool.description if hasattr(tool, "description") and tool.description else "No description"
            choice_title = f"{tool.name} - {description}"
            choices.append(questionary.Choice(choice_title, tool.name))

        tool_name = await questionary.select(
            "Select a tool:", choices=choices, use_search_filter=True, use_jk_keys=False
        ).ask_async()

        return tool_name
