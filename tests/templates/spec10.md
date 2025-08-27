# Task Template

## Image links

{% set image = call_tool('test-mcp', 'get_blob', {}) %}

{{ image }}

## Multiple contents

{% set contents = call_tool('test-mcp', 'multi_content_response', {}) %}

{{ contents }}

## Structured data

{% set weather = call_tool('test-mcp', 'get_weather', {'city': 'New York'}) %}

### Weather Information
- Temperature: {{ weather.temperature }}°C
- Condition: {{ weather.condition }}