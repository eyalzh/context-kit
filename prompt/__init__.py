import questionary

# Add interactive prompt helpers using questionary that will collect values for
# unspecified template variables.


async def collect_var_value(var_name: str) -> str:
    """Collect a value for a variable using questionary."""

    return await questionary.text(f"Please provide a value for '{var_name}':").ask_async()
