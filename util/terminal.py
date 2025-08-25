import os


def supports_hyperlinks():
    # Check if terminal supports hyperlinks
    return (
        os.getenv("TERM_PROGRAM") in ["iTerm.app", "vscode"]
        or os.getenv("COLORTERM") == "truecolor"
        or "hyperlinks" in os.getenv("TERM", "")
    )


def underline(text):
    return f"\033[4m{text}\033[0m"


def display_hyperlink(url):
    if supports_hyperlinks():
        return f"\033]8;;{url}\033\\{url}\033]8;;\033\\"
    else:
        return url
