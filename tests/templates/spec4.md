# Task

Please complete the task described below. Start by planning...

## Ticket

{% set ticket = call_tool('test-mcp', 'jsonTest', {'cloudId': '1234', 'ticketId': ticket_id}) %}

Ticket ID: {{ ticket.id }}

### Description
{{ ticket.description }}
