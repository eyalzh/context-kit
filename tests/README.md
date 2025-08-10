# E2E tests

## Running Tests
```
uv run pytest
```

## Manual Testing

```
uv run cxk.py create-spec tests/templates/spec1.md
```

```
uv run cxk.py create-spec tests/templates/spec1.md --output result.md
```

```
uv run cxk.py create-spec tests/templates/spec1.md --var additional_context=aa --var ticket='{"id":1}'
```