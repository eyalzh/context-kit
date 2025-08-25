# Task Template

## Ticket description

{% set ticket1 = call_tool('linear-test', 'get_issue', {'id': 'MCP-1'}) %}
{% set ticket2 = call_tool('linear-test', 'get_issue', {'id': 'MCP-2'}) %}

### Description
{{ ticket1.description }}

### Other Description
{{ ticket2.description }}
