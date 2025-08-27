# Task Template

## Image links

{% set issue = call_tool('github', 'get_issue', {'issue_number': 17, 'owner': 'eyalzh', 'repo': 'browser-control-mcp'}) %}

### Github Issue Description
{{ issue.body }}