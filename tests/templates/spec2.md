# Task Template

## Ticket description

{% set ticket = call_tool('test-mcp', 'jsonTest', {'cloudId': '1234', 'ticketId': 'ACME-123'}) %}

{{ ticket.id }}

### Description
{{ ticket.description }}

## Additional context

{{ additional_context }}