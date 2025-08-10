import json
import logging
import os
import sys

from engine import TemplateEngine, TemplateParseError
from prompt import collect_var_value


async def handle_create_spec(
    spec_template: str | None,
    output_file: str | None = None,
    var_overrides: list[str] | None = None,
    verbose: bool = False,
):
    log_level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="%(message)s", force=True)

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

        template_engine = TemplateEngine.from_file(template_path)
    elif stdin_piped:
        try:
            template_str = sys.stdin.read()
        except Exception as e:
            logging.error(f"Error: Failed to read from stdin: {e}")
            sys.exit(1)
        if not template_str:
            logging.error("Error: No data received on stdin for template")
            sys.exit(1)

        template_engine = TemplateEngine.from_string(template_str)
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
                    raw_value = await collect_var_value(var)
                logging.info(f"  {var}: {raw_value}")

                # Try to parse as JSON if it looks like JSON
                if raw_value and (raw_value.strip().startswith("{") or raw_value.strip().startswith("[")):
                    try:
                        collected_vars[var] = json.loads(raw_value)
                    except json.JSONDecodeError:
                        # If it's not valid JSON, use as string
                        collected_vars[var] = raw_value
                else:
                    collected_vars[var] = raw_value
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
        logging.error(f"Error: Failed to process template: {e}")
        sys.exit(1)
