# Task Template

## Ticket description

{% set ticket = call_tool('jira', 'getJiraIssue', {'cloudId': '483da417-278f-434d-8baf-132455657f48', 'issueIdOrKey': 'SCRUM-5'}) %}

### Description
{{ ticket.fields.description }}

## Information from greeting service

{{ get_resource('test-mcp', 'greeting://foobar') }}

## Another ticket description

{% set ticket = call_tool('jira', 'getJiraIssue', {'cloudId': '483da417-278f-434d-8baf-132455657f48', 'issueIdOrKey': 'SCRUM-4'}) %}

### Description
{{ ticket.fields.description }}