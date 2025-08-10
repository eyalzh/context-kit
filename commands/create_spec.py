import json
import logging
import os
import sys

from engine import TemplateEngine, TemplateParseError
from prompt import collect_var_value


async def handle_create_spec(spec_template: str, output_file: str | None = None, var_overrides: list[str] | None = None, verbose: bool = False):
    """Handle the create-spec command"""

    # Configure logging based on verbose flag
    log_level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=log_level, format='%(message)s', stream=sys.stdout, force=True)

    # Resolve relative paths against current working directory
    template_path = os.path.abspath(spec_template)

    # Check if template file exists
    if not os.path.exists(template_path):
        print(f"Error: Template file '{spec_template}' not found", file=sys.stderr)
        sys.exit(1)

    try:
        # Initialize template engine
        template_engine = TemplateEngine(template_path)

        # Get variables from template
        variables = template_engine.get_variables()

        # Parse var_overrides into a dictionary
        provided_vars = {}
        if var_overrides:
            for var_override in var_overrides:
                if '=' not in var_override:
                    print(f"Error: Invalid variable format '{var_override}'. Use KEY=VALUE format.", file=sys.stderr)
                    sys.exit(1)
                key, value = var_override.split('=', 1)
                provided_vars[key] = value

        # Collect values for each variable
        collected_vars = {}
        if variables:
            logging.info("Collecting values for template variables:")
            for var in sorted(variables):
                if var in provided_vars:
                    raw_value = provided_vars[var]
                    logging.info(f"  {var}: {raw_value}")
                else:
                    raw_value = await collect_var_value(var)
                    logging.info(f"  {var}: {raw_value}")

                # Try to parse as JSON if it looks like JSON
                if raw_value and (raw_value.strip().startswith('{') or raw_value.strip().startswith('[')):
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
            with open(output_path, 'w') as f:
                f.write(rendered_content)
            logging.info(f"Rendered template saved to: {output_path}")
        else:
            logging.debug("\nRendered template:")
            print(rendered_content)

    except TemplateParseError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to process template: {e}", file=sys.stderr)
        sys.exit(1)
