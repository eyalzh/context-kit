
import os
import sys

from engine import TemplateEngine, TemplateParseError


# Create spec command:
# cxk create-spec [spec-template]
# Will output into stdout the rendered spec file
#
# For now all it does is to use TemplateEngine to print the list of variables in the template and nothing more.
# It also prints an error if the template is not found or cannot be parsed.


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

        # Print list of variables
        if variables:
            print("Template variables:")
            for var in sorted(variables):
                print(f"  - {var}")
        else:
            print("No variables found in template")

    except TemplateParseError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to process template: {e}", file=sys.stderr)
        sys.exit(1)
