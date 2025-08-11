# E2E tests

## Running Tests
```
uv run pytest
```

## Manual Testing

### Initialize the environment and adding mcp configuration
```
uv run cxk.py init
uv run cxk.py mcp add-stdio server-name2 --env KEY=value -- python server.py
```

```
uv run cxk.py create-spec tests/templates/spec1.md
```

```
uv run cxk.py create-spec tests/templates/spec1.md --output result.md
```

```
uv run cxk.py create-spec tests/templates/spec1.md --var additional_context=aa --var ticket='{"id":1}'
```

### With verbose, vars and output
```
uv run cxk.py create-spec tests/templates/spec1.md --verbose --var additional_context=1 --var ticket='{"id":1}' --output res.md
```

### Piped
```
cat tests/templates/spec1.md | uv run cxk.py create-spec --verbose --var ticket='{"id":1}' --var additional_context=2
```

### With MCP functions
```
uv run cxk.py create-spec tests/templates/spec2.md
```