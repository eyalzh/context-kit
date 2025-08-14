# Task Template

## Ticket description

{% set ticket = call_tool('test-mcp', 'jsonTest', {'cloudId': '1234'}) %}

{{ ticket.id }}

### Description
{{ ticket.description }}

## Additional context

{{ additional_context }}

## Some math...

{{ call_tool('test-mcp', 'add', {'a': 5}) }}
