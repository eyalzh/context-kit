import logging
import os
import sys

from engine import TemplateEngine, TemplateParseError
from mcp_client import get_session_manager
from prompt import PromptHelper
from state import State
from util.parse import parse_input_string


async def handle_create_spec(
    spec_template: str | None,
    state: State,
    output_file: str | None = None,
    var_overrides: list[str] | None = None,
):
    # Initialize session manager without pre-initializing all servers
    session_manager = get_session_manager()
    try:
        # Set the state in session manager for on-demand initialization
        session_manager.set_state(state)
        prompt_helper = PromptHelper(state)

        # Detect piped input (stdin not a TTY) and ensure there's data before using it
        stdin_piped = not sys.stdin.isatty()

        # Determine template source
        template_engine: TemplateEngine
        if spec_template:
            # Resolve relative paths against current working directory
            template_path = os.path.abspath(spec_template)

            # Check if template file exists
            if not os.path.exists(template_path):
                logging.error(f"Error: Template file '{spec_template}' not found")
                sys.exit(1)

            template_engine = TemplateEngine.from_file(template_path, state, prompt_helper)
        elif stdin_piped:
            try:
                template_str = sys.stdin.read()
            except Exception as e:
                logging.error(f"Error: Failed to read from stdin: {e}")
                sys.exit(1)
            if not template_str:
                logging.error("Error: No data received on stdin for template")
                sys.exit(1)

            template_engine = TemplateEngine.from_string(template_str, state, prompt_helper)
        else:
            logging.error("Error: Missing spec_template argument (or provide template via stdin)")
            sys.exit(1)

        try:
            variables = template_engine.get_variables()

            # Parse var_overrides into a dictionary
            provided_vars = {}
            if var_overrides:
                for var_override in var_overrides:
                    if "=" not in var_override:
                        logging.error(f"Error: Invalid variable format '{var_override}'. Use KEY=VALUE format.")
                        sys.exit(1)
                    key, value = var_override.split("=", 1)
                    provided_vars[key] = value

            # Collect values for each variable
            collected_vars = {}
            if variables:
                logging.info("Collecting values for template variables:")
                for var in sorted(variables):
                    if var in provided_vars:
                        raw_value = provided_vars[var]

                    else:
                        # Interactive mode: user chooses between direct value or MCP tool
                        raw_value = await prompt_helper.collect_var_value_interactive(var)
                    logging.info(f"  {var}: {raw_value}")

                    collected_vars[var] = parse_input_string(raw_value)

            else:
                logging.info("No variables found in template")

            # Render the template with collected variables
            rendered_content = await template_engine.render_async(**collected_vars)

            # Output to file or stdout
            if output_file:
                output_path = os.path.abspath(output_file)
                with open(output_path, "w") as f:
                    f.write(rendered_content)
                logging.info(f"Rendered template saved to: {output_path}")
            else:
                logging.debug("\nRendered template:")
                print(rendered_content)

        except TemplateParseError as e:
            logging.error(f"Error: {e}")
            sys.exit(1)
        except Exception as e:
            logging.exception(f"Error: Failed to process template")
            sys.exit(1)

    finally:
        # Clean up all MCP sessions
        await session_manager.cleanup()
