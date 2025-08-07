import json
import os
import sys

from engine import TemplateEngine, TemplateParseError
from prompt import collect_var_value


async def handle_create_spec(spec_template: str):
    """Handle the create-spec command"""

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

        # Collect values for each variable
        collected_vars = {}
        if variables:
            print("Collecting values for template variables:")
            for var in sorted(variables):
                raw_value = await collect_var_value(var)
                print(f"  {var}: {raw_value}")

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
            print("No variables found in template")

        # Render the template with collected variables
        rendered_content = await template_engine.render_async(**collected_vars)
        print("\nRendered template:")
        print(rendered_content)

    except TemplateParseError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to process template: {e}", file=sys.stderr)
        sys.exit(1)
