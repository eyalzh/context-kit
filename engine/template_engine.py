from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template, meta, select_autoescape

from engine.globals import create_mcp_resource_function, create_mcp_tool_function
from prompt import PromptHelper
from state import State


class TemplateParseError(Exception):
    pass


class TemplateEngine:
    def __init__(
        self,
        env: Environment,
        template: Template,
        state: State,
        prompt_helper: PromptHelper,
        source_path: Path | None = None,
        source_string: str | None = None,
    ):
        """Private constructor - use from_file() or from_string() instead"""
        self.env = env
        self.template = template
        self._source_path = source_path
        self._source_string = source_string
        self._state = state
        self._prompt_helper = prompt_helper

        # Add global functions to env to support MCP tools and resources
        self.env.globals["call_tool"] = create_mcp_tool_function(self._prompt_helper, self._state)
        self.env.globals["get_resource"] = create_mcp_resource_function(self._state)

    @classmethod
    def from_file(cls, path: str | Path, state: State, prompt_helper: PromptHelper) -> "TemplateEngine":
        """Create a TemplateEngine from a template file.

        Args:
            path: Path to the template file
            state: State object containing project configuration

        Returns:
            TemplateEngine instance

        Raises:
            FileNotFoundError: If template file doesn't exist
            TemplateParseError: If template parsing fails
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Template file not found: {path}")

        template_dir = path.parent
        template_name = path.name

        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(),
            enable_async=True,
        )

        try:
            template = env.get_template(template_name)
        except Exception as e:
            raise TemplateParseError(f"Failed to load template from {path}: {e}") from e

        return cls(
            env=env, template=template, state=state, source_path=path, source_string=None, prompt_helper=prompt_helper
        )

    @classmethod
    def from_string(
        cls, template_string: str, state: State, prompt_helper: PromptHelper, name: str = "<stdio>"
    ) -> "TemplateEngine":
        """Create a TemplateEngine from a template string.

        Args:
            template_string: The template content as a string
            state: State object containing project configuration
            name: Optional name for the template (for debugging)

        Returns:
            TemplateEngine instance

        Raises:
            TemplateParseError: If template parsing fails
        """

        env = Environment(
            autoescape=select_autoescape(),
            enable_async=True,
        )

        try:
            template = env.from_string(template_string)
        except Exception as e:
            raise TemplateParseError(f"Failed to parse template string: {e}") from e

        # Store the name in the template for better error messages
        template.name = name

        return cls(
            env=env,
            template=template,
            state=state,
            source_path=None,
            source_string=template_string,
            prompt_helper=prompt_helper,
        )

    @property
    def source(self) -> str:
        """Get the template source content."""
        if self._source_string is not None:
            return self._source_string

        if self._source_path is not None:
            with open(self._source_path, encoding="utf-8") as f:
                return f.read()

        # Should not reach here with proper factory method usage
        raise AssertionError("No template source available")

    @property
    def path(self) -> Path | None:
        """Get the template file path if loaded from file."""
        return self._source_path

    @property
    def is_from_file(self) -> bool:
        """Check if template was loaded from a file."""
        return self._source_path is not None

    def get_variables(self) -> set[str]:
        """Get the free (undeclared) variables in the template.

        Returns:
            Set of variable names that are referenced but not defined in the template

        Raises:
            TemplateParseError: If template parsing fails
        """
        try:
            ast = self.env.parse(self.source)
        except Exception as e:
            raise TemplateParseError(f"Failed to parse template: {e}") from e

        # Find all undeclared variables
        variables = meta.find_undeclared_variables(ast)
        return variables

    async def render_async(self, *args: Any, **kwargs: Any) -> str:
        return await self.template.render_async(*args, **kwargs)

    def __repr__(self) -> str:
        if self._source_path:
            return f"TemplateEngine(from_file={self._source_path})"
        else:
            name = self.template.name if hasattr(self.template, "name") else "<stdio>"
            return f"TemplateEngine(from_string, name={name})"
