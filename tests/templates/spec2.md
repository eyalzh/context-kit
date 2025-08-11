# Task Template

## Ticket description

{% set ticket = mcp('jira', 'getJiraIssue', {'issueKey': 'ACME-4432'}) %}

{{ ticket.id }}

{{ ticket.description }}

## Additional context

{{ additional_context }}