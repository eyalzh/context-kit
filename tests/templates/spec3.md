# Task Template

## Ticket description

{% set ticket = mcp('test-mcp', 'jsonTest', {'cloudId': '1234'}) %}

{{ ticket.id }}

### Description
{{ ticket.description }}

## Additional context

{{ additional_context }}

## Some math...

{{ mcp('test-mcp', 'add', {'a': 5}) }}
