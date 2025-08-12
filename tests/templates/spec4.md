# Task Template

## Ticket description

{% set ticket = mcp('test-mcp', 'jsonTest', {'cloudId': '1234', 'ticketId': ticket_id}) %}

{{ ticket.id }}

### Description
{{ ticket.description }}
