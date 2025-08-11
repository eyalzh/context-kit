from typing import TYPE_CHECKING

import questionary
from state import State

# Add interactive prompt helpers using questionary that will collect values for
# unspecified template variables.


class PromptHelper:

    def __init__(
        self,
        state: State,
    ):
        self._state = state

    async def collect_var_value(self, var_name: str) -> str:
        """Collect a value for a variable using questionary."""

        return await questionary.text(f"Please provide a value for '{var_name}':").ask_async()

    async def get_full_args(self, tools, tool_name, args):
        """
        Get full arguments for the tool call, using collect_tool_input() to collect missing required fields.

        :param tools: List of available tools
        :param tool_name: Name of the tool to call
        :param args: Arguments provided by the user
        :return: Full arguments including defaults and required fields
        """
        selected_tool = next((t for t in tools.tools if t.name == tool_name), None)
        if not selected_tool:
            raise ValueError(f"Tool '{tool_name}' not found.")

        input_schema = selected_tool.inputSchema
        if not input_schema:
            return args

        # Use collect_tool_input to fill in missing required fields
        full_args = await self.collect_tool_input(input_schema, args, include_optional=False)

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

            print(f"Collecting input for field: {field_info}")
            title = field_info["title"] if "title" in field_info else field_name
            field_type = field_info["type"] if "type" in field_info else "string"
            field_desc = field_info.get("description", None)
            is_required = field_name in required

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

            if field_type == "integer":
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
