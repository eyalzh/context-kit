# ContextKit 🔧

A CLI tool and MCP client for creating spec files for AI coding agents. ContextKit generates specs from reusable Jinja2-based templates, filling in context from various MCP sources and user input.

**Note**: While ContextKit is an MCP client, it doesn't use an AI model - it's a tool to harness the MCP ecosystem for context injection.

## How it Works 🚀

ContextKit utilizes the MCP (Model Context Protocol) ecosystem to inject context into spec files from various sources like ticketing systems, databases, document storage, and design tools. It works with spec templates - reusable Jinja2 template files containing context variables that define the common structure and requirements of development tasks.

Context variables are automatically fetched from MCP resources when possible, or collected interactively from the user when additional input is needed.

## Installation 📦

### Requirements
- Python 3.11 or higher

### Install from source

```bash
git clone <repository-url>
cd context-kit
uv sync
```

### Install in editable mode

```bash
pip install -e .
```

After editable installation, you can use the `cxk` command directly:
```bash
cxk --help
```

Alternatively, without editable installation:
```bash
python cxk.py --help
# or with uv:
uv run cxk.py --help
```

## Quick Start 🏃

### 1. Initialize a project
Run this in your project directory. It creates a `.cxk/` directory to store config.
```bash
cxk init
```

### 2. Add MCP servers
```bash
# Add SSE server
cxk mcp add-sse jira-server http://localhost:3000

# Add stdio server with environment
cxk mcp add-stdio local-tools --env API_KEY=secret -- python server.py

# Add HTTP server
cxk mcp add-http doc-service http://localhost:8000
```

### 3. Create a spec from template
```bash
cxk create-spec path/to/template.md
```

## Usage Examples 💻

### Basic Template with MCP Tool Call

**Template (spec.md):**
```markdown
{% set ticket = call_tool('jira', 'getJiraIssue', {'cloudId': '1234', 'issueKey': ticket_id}) %}

## Task Description
{{ ticket.fields.description }}

## Acceptance Criteria
{{ ticket.fields.acceptance_criteria }}
```

**Generate spec:**
```bash
cxk create-spec spec.md --var ticket_id=ACME-123
```

### Template with MCP Resource

**Template (design-spec.md):**
```markdown
## Design Requirements
{{ get_resource('figma-service', 'designs://'+design_id) }}
```

**Generate spec:**
```bash
cxk create-spec design-spec.md --var design_id=fig-456
```

### Advanced: Filtering and Processing Context

**Filter sensitive information:**
```markdown
{% set support_ticket = call_tool('support', 'getTicket', ticket_id) %}
## Support Request
{{ support_ticket | regex_replace(r'\b[\w.+-]+@[\w.-]+\.\w+\b', '[EMAIL_REDACTED]') }}
```

**Extract specific fields:**
```markdown
{% set ticket = call_tool('jira', 'getJiraIssue', {'issueKey': ticket_id}) %}
## Summary
{{ ticket.fields.summary }}

## Priority
{{ ticket.fields.priority.name }}
```

### Interactive Variable Collection

When variables aren't provided via `--var`, ContextKit prompts interactively:

```bash
cxk create-spec template.md
# Prompts:
# ? How would you like to provide the value for 'ticket_id'?
#   › Provide value directly
#     Use MCP tool to fetch value
```

### Output to File

```bash
cxk create-spec template.md --output result.md --var ticket_id=ACME-123
```

### Pipe Template Content

```bash
cat template.md | cxk create-spec --var ticket_id=ACME-123
```

## CLI Commands 🛠️

### Project Management

```bash
# Initialize new project (creates .cxk/ directory)
cxk init
```

### MCP Server Management

```bash
# Add SSE MCP server
cxk mcp add-sse <server-name> <websocket-url>

# Add stdio MCP server
cxk mcp add-stdio <server-name> [--env KEY=value] -- <command> [args...]

# Add HTTP MCP server  
cxk mcp add-http <server-name> <http-url> [--header KEY=value]
```

### Spec Generation

```bash
# Generate spec from template
cxk create-spec <template-path> [--var KEY=value] [--output <file>]

# Generate with multiple variables
cxk create-spec template.md --var ticket_id=ACME-123 --var env=production
```

## Template Language 📝

ContextKit uses **Jinja2** as its template engine with additional global functions:

### Available Functions

- `call_tool(server_name, tool_name, arguments)` - Call MCP tool
- `get_resource(server_name, resource_uri)` - Get MCP resource
- All standard Jinja2 filters and functions

### Template Variables

Variables can be:
- **Direct values**: `--var ticket_id=ACME-123`
- **JSON objects**: `--var ticket='{"id": 123, "status": "open"}'`
- **Interactive input**: Prompted when not provided

## Configuration 📋


### MCP Configuration Examples

```bash
# Development setup
cxk init
cxk mcp add-sse jira https://mcp.example.com/jira
cxk mcp add-stdio local-db --env DB_URL=postgresql://... -- python db_server.py
cxk mcp add-http docs http://localhost:8000 --header Authorization='Bearer token'
```

## Why ContextKit? 🤔

### Benefits
- **🚀 Speed**: Pre-populate specs with relevant context automatically
- **💰 Cost reduction**: AI agents don't need to make additional MCP calls
- **🧹 Clean codebase**: Keep reusable spec templates in version control
- **🔄 Consistency**: Standardized spec format across your team
- **🔌 Extensible**: Leverage the growing MCP ecosystem


## Development 🔨

```bash
# Install development dependencies
uv sync

# Run tests
uv run pytest

# Run linting
uv run ruff check
uv run ruff format
```
