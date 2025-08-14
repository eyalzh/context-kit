# Task Template

## Ticket description

{% set ticket = call_tool('test-mcp', 'jsonTest', {'cloudId': '1234', 'ticketId': ticket_id}) %}

{{ ticket.id }}

### Description
{{ ticket.description }}
