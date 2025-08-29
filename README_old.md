# ContextKit
ContextKit automates and speeds up the process of creating spec files for coding agents. It generates specs from reusable templates, filling in context from various sources using MCP and user input.

In other words, instead of creating or modifying spec files for each task in a project, ContextKit allows developers to define reusable spec templates for development tasks, and only provide task-specific context when generating the spec such as a ticket ID or Figma URL.

## How it works
By being an MCP client, ContextKit utilizes the evolving MCP ecosystem to inject context into spec files from various sources, such as ticketing systems, databases, document storage, and design tools. It works with spec templates - reusable spec files, containing context variables, that define the common structure and requirements of tasks in a project. The context variables are either fully specified or partially specified MCP resources and tools.

If a context variable can be fulfilled by fetching an MCP resource, then it will be automatically fetched and injected into the spec file when generating the spec. If the context variable is a partial MCP resource, the user will be prompted to complete it before the spec file is generated. Usually the missing arguments in the MCP resource or tool are task-specific, such as a ticket ID or a Figma URL.

## Real world example
- Show task template like spec4.md
- Show how running full command with --var ticket_id=ACME-123 result in a spec file 

## But why?
- Reduce cost and time. AI agents won't need to make additional MCP calls.
- Cleaner codebase: Keep spec templates in your codebase rather than specific task related documents.

## Installation

### Install from source (development)

1. Clone the repository:
```bash
git clone <repository-url>
cd context-kit
```

2. Install in editable mode:
```bash
pip install -e .
```

After installation, you can use the `cxk` command:
```bash
cxk --help
```

### Requirements
- Python 3.11 or higher

## Usage

### Add MCP tool calls with variables

```
# Spec Template (spec.md)
{% set ticket = call_tool('jira', 'getJiraIssue', {'cloudId': '1234', 'issueKey': ticket_id}) %}

### Description
{{ ticket.description }}
```

Generating the spec with a ticket ID:
```
cxk create-spec spec.md --var ticket_id=ACME-123
```

This will fetch the ticket and add its description to the spec file.

### Add MCP resources with variables
```
# Spec Template (spec.md)
## PRD
{{ get_resource('doc-storage-service', 'docs://'+prd_id) }}
```

Generating the spec with a PRD ID:
```
cxk create-spec spec.md --var prd_id=PRD-456
```

### Filtering context

MCP resources can quickly oversaturate the context. With the template engine, you can apply filters and selectors to include only relevant parts of resources. For example:

```
## Ticket description
{% set ticket_info = call_tool('jira', 'getJiraIssue', {'issueKey': 'ACME-4432'}) %}
{{ ticket_info.fields.description }}
```

You can also filter resources to mask sensitive information:

```
## Support ticket
{% set support_ticket_info = call_tool('support', 'getTicket', 'ACME-9912') %}
{{ support_ticket_info | regex_replace(r'\b[\w.+-]+@[\w.-]+\.\w+\b', '[EMAIL_REDACTED]') }}
```

### Interactively selecting MCP resources and tools

Template variables can be given values either directly or by selecting an MCP tool to call. For example:

```
# Spec Template (spec.md)

## Task description
{{ task }}
```

Running create-spec will then prompt you to either provide a direct value for `task` or select an MCP server, tool and args to call to fetch the task description.

```
? How would you like to provide the value for 'task'? (Use arrow keys)
 » Provide value directly
   Use MCP tool to fetch value
```


### Initialize a project
```
cxk init
```
Initialize a new ContextKit project in the current directory.

### MCP Server Management

Add an SSE MCP server:
```
cxk mcp add-sse <server-name> <url>
```

Add a stdio MCP server:
```
cxk mcp add-stdio <server-name> [--env key=value] -- <command> [args...]
```

Add an HTTP MCP server:
```
cxk mcp add-http <server-name> <url> [--header key=value]
```

### MCP Configuration Examples

```
# Initialize a new project
cxk init

# Add an SSE server
cxk mcp add-sse my-server https://mcp.example.com/v1/sse

# Add a stdio server with environment variables
cxk mcp add-stdio my-stdio-server --env API_KEY=secret -- python server.py

# Add an HTTP server
cxk mcp add-http my-http-server http://localhost:8000 --header Authorization='Bearer ....'
```

