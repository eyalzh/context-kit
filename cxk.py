import argparse
import asyncio
import sys

from commands.create_spec import handle_create_spec
from commands.init import handle_init
from commands.mcp import (
    MCPAddHttpContext,
    MCPAddSSEContext,
    MCPAddStdioContext,
    MCPCommandContext,
    handle_mcp,
)
from state import State


async def main():
    parser = argparse.ArgumentParser(description="ContextKit CLI tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # cxk init
    subparsers.add_parser("init", help="Initialize a new ContextKit project")

    # cxk create-spec [spec-template]
    create_spec_parser = subparsers.add_parser("create-spec", help="Create spec from template")
    create_spec_parser.add_argument("spec_template", help="Path to the spec template file")

    # cxk mcp
    mcp_parser = subparsers.add_parser("mcp", help="Manage MCP servers")
    mcp_subparsers = mcp_parser.add_subparsers(dest="mcp_command", help="MCP commands")

    # cxk mcp add-sse [server-name] [url]
    add_sse_parser = mcp_subparsers.add_parser("add-sse", help="Add SSE MCP server")
    add_sse_parser.add_argument("server_name", help="Name of the server")
    add_sse_parser.add_argument("url", help="URL of the SSE server")

    # cxk mcp add-stdio [server-name] --env [env-var] -- [command]
    add_stdio_parser = mcp_subparsers.add_parser("add-stdio", help="Add stdio MCP server")
    add_stdio_parser.add_argument("server_name", help="Name of the server")
    add_stdio_parser.add_argument("--env", action="append", help="Environment variable (key=value)")
    add_stdio_parser.add_argument("command_line", nargs=argparse.ONE_OR_MORE, help="Command to run")

    # cxk mcp add-http [server-name] [url]
    add_http_parser = mcp_subparsers.add_parser("add-http", help="Add HTTP MCP server")
    add_http_parser.add_argument("server_name", help="Name of the server")
    add_http_parser.add_argument("url", help="URL of the HTTP server")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    state = State()

    try:
        if args.command == "init":
            await handle_init(state)

        elif args.command == "create-spec":
            await handle_create_spec(args.spec_template)

        elif args.command == "mcp":
            if not args.mcp_command:
                mcp_parser.print_help()
                sys.exit(1)

            if args.mcp_command == "add-sse":
                mcp_context = MCPCommandContext(
                    subcommand="add-sse",
                    add_sse=MCPAddSSEContext(server_name=args.server_name, url=args.url),
                )
                await handle_mcp(state, mcp_context)

            elif args.mcp_command == "add-stdio":
                mcp_context = MCPCommandContext(
                    subcommand="add-stdio",
                    add_stdio=MCPAddStdioContext(
                        server_name=args.server_name,
                        env=args.env,
                        command=args.command_line,
                    ),
                )
                await handle_mcp(state, mcp_context)

            elif args.mcp_command == "add-http":
                mcp_context = MCPCommandContext(
                    subcommand="add-http",
                    add_http=MCPAddHttpContext(server_name=args.server_name, url=args.url),
                )
                await handle_mcp(state, mcp_context)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
