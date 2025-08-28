from pydantic import BaseModel

from mcp_client import HTTPServerConfig, SSEServerConfig, StdioServerConfig
from state import State


class MCPAddSSEContext(BaseModel):
    server_name: str
    url: str


class MCPAddStdioContext(BaseModel):
    server_name: str
    env: list[str] | None = None
    command: list[str]


class MCPAddHttpContext(BaseModel):
    server_name: str
    url: str
    headers: list[str] | None = None


class MCPCommandContext(BaseModel):
    subcommand: str
    add_sse: MCPAddSSEContext | None = None
    add_stdio: MCPAddStdioContext | None = None
    add_http: MCPAddHttpContext | None = None


async def handle_mcp_command(state: State, context: MCPCommandContext):
    if not state.is_initialized:
        print("Project not initialized. Run 'cxk init' first.")
        return

    if context.subcommand == "add-sse" and context.add_sse:
        await handle_add_sse(state, context.add_sse.server_name, context.add_sse.url)

    elif context.subcommand == "add-stdio" and context.add_stdio:
        env_dict = {}
        if context.add_stdio.env:
            for env_var in context.add_stdio.env:
                if "=" in env_var:
                    key, value = env_var.split("=", 1)
                    env_dict[key] = value
                else:
                    raise ValueError(f"Invalid environment variable format: {env_var}. Use KEY=VALUE format.")

        await handle_add_stdio(
            state,
            context.add_stdio.server_name,
            context.add_stdio.command,
            env_dict if env_dict else {},
        )

    elif context.subcommand == "add-http" and context.add_http:
        headers_dict = {}
        if context.add_http.headers:
            for header in context.add_http.headers:
                if "=" in header:
                    key, value = header.split("=", 1)
                    headers_dict[key] = value
                else:
                    raise ValueError(f"Invalid header format: {header}. Use KEY=VALUE format.")

        await handle_add_http(
            state,
            context.add_http.server_name,
            context.add_http.url,
            headers_dict if headers_dict else None,
        )


async def handle_add_sse(state: State, server_name: str, url: str):
    if server_name in state.mcp_config.mcpServers:
        raise ValueError(f"Server '{server_name}' already exists")

    server_config = SSEServerConfig(url=url)
    state.mcp_config.mcpServers[server_name] = server_config
    state.save_mcp_config()

    print(f"Added SSE server '{server_name}' with URL: {url}")


async def handle_add_stdio(
    state: State,
    server_name: str,
    command: list[str],
    env: dict[str, str] | None = None,
):
    if server_name in state.mcp_config.mcpServers:
        raise ValueError(f"Server '{server_name}' already exists")

    # First argument is the command, rest are args

    cmd = command[0]
    args = command[1:] if len(command) > 1 else None

    server_config = StdioServerConfig(command=cmd, args=args, env=env)
    state.mcp_config.mcpServers[server_name] = server_config
    state.save_mcp_config()

    print(f"Added stdio server '{server_name}' with command: {' '.join(command)}")
    if env:
        print(f"Environment variables: {env}")


async def handle_add_http(state: State, server_name: str, url: str, headers: dict[str, str] | None = None):
    if server_name in state.mcp_config.mcpServers:
        raise ValueError(f"Server '{server_name}' already exists")

    server_config = HTTPServerConfig(url=url, headers=headers)
    state.mcp_config.mcpServers[server_name] = server_config
    state.save_mcp_config()

    print(f"Added HTTP server '{server_name}' with URL: {url}")
    if headers:
        print(f"Headers: {headers}")
