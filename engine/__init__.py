import os
from typing import Any

from jinja2 import Environment, FileSystemLoader, meta, select_autoescape


class TemplateParseError(Exception):
    pass


class TemplateEngine:
    """Abstract away the jinja2 template engine"""

    def __init__(self, template_path: str):
        template_dir = os.path.dirname(template_path)
        template_name = os.path.basename(template_path)

        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(),
        )
        self.template = self.env.get_template(template_name)
        self.template_path = template_path

    def get_variables(self) -> set[str]:
        """Get the free variables in the template"""

        with open(self.template_path, encoding="utf-8") as f:
            template_source = f.read()

        try:
            ast = self.env.parse(template_source)
        except Exception as e:
            raise TemplateParseError(f"Failed to parse template: {e}") from e

        # Find all undeclared variables
        variables = meta.find_undeclared_variables(ast)
        return variables

    async def render_async(self, *args: Any, **kwargs: Any) -> str:
        return await self.template.render_async(*args, **kwargs)
