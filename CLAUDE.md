# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ContextKit is a CLI tool and MCP (Model Context Protocol) client for creating spec files for AI coding agents. It uses reusable spec templates with context variables that can be automatically filled from various MCP sources (ticketing systems, databases, design tools, etc.).

## Architecture

- **Entry point**: `cxk.py` - Main CLI with argparse-based command routing
- **State management**: `state.py` - Handles project initialization, config loading, and git repo detection
- **Command handlers**: `commands/` directory contains handlers for each CLI command:
  - `init.py` - Project initialization (creates `.cxk/` config directory)
  - `mcp.py` - MCP server management (add-sse, add-stdio, add-http)
  - `create_spec.py` - Template rendering with variable collection
- **Template engine**: `engine/` - Jinja2-based template processing
- **MCP configuration**: `util/mcp/config.py` - Pydantic models for MCP server configs
- **User prompts**: `prompt/` - Interactive variable collection

## Core Concepts

1. **Project state**: Must be initialized with `cxk init` (creates `.cxk/mcp.json`)
2. **MCP servers**: Configured via CLI commands, stored in `.cxk/mcp.json`
3. **Spec templates**: Jinja2 templates with variables that get filled from MCP resources
4. **Context variables**: Can be automatic MCP resources or user-provided values

## Common Commands

### Development
```bash
# Install dependencies
uv sync

# Run tests
uv run pytest
# Alternative test runner
python run_tests.py

# Linting and formatting
uv run ruff check
uv run ruff format
```

### CLI Usage
```bash
# Initialize project (creates .cxk/ directory)
python cxk.py init

# Add MCP servers
python cxk.py mcp add-sse server-name ws://localhost:3000
python cxk.py mcp add-stdio server-name --env KEY=value -- python server.py
python cxk.py mcp add-http server-name http://localhost:8000

# Create spec from template
python cxk.py create-spec path/to/template.md
```

## Key Files

- `pyproject.toml` - Python dependencies, ruff configuration (line length: 120, Python 3.12+)
- `pytest.ini` - Test configuration (async mode enabled)
- `.cxk/mcp.json` - MCP server configuration (created after init)
- `tests/templates/spec1.md` - Example template with Jinja2 variables

## Development Notes

- Uses async/await throughout for MCP client compatibility
- Pydantic models for configuration validation
- Git repository detection required for project initialization
- Template variables can be JSON objects or strings
- MCP server configurations support stdio, SSE, and HTTP transports (HTTP not fully implemented)