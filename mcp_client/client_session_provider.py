from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from urllib.parse import parse_qs, urlparse

from .config import MCPServersConfig, SSEServerConfig, StdioServerConfig
from mcp import ClientSession, StdioServerParameters
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
from pydantic import AnyUrl


class InMemoryTokenStorage(TokenStorage):
    """Demo In-memory token storage implementation."""

    def __init__(self):
        self.tokens: OAuthToken | None = None
        self.client_info: OAuthClientInformationFull | None = None

    async def get_tokens(self) -> OAuthToken | None:
        """Get stored tokens."""
        return self.tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        """Store tokens."""
        self.tokens = tokens

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        """Get stored client information."""
        return self.client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        """Store client information."""
        self.client_info = client_info


async def handle_redirect(auth_url: str) -> None:
    print(f"Visit: {auth_url}")


async def handle_callback() -> tuple[str, str | None]:
    callback_url = input("Paste callback URL: ")
    params = parse_qs(urlparse(callback_url).query)
    return params["code"][0], params.get("state", [None])[0]


@asynccontextmanager
async def get_stdio_session(server_params: StdioServerParameters):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            yield session


@asynccontextmanager
async def get_streamablehttp_session(server_url: str):
    oauth_auth = OAuthClientProvider(
        server_url=server_url,
        client_metadata=OAuthClientMetadata(
            client_name="Example MCP Client",
            redirect_uris=[AnyUrl("http://localhost:3000/callback")],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            scope="user",
        ),
        storage=InMemoryTokenStorage(),
        redirect_handler=handle_redirect,
        callback_handler=handle_callback,
    )
    # Connect to a streamable HTTP server
    async with streamablehttp_client(server_url, auth=oauth_auth) as (
        read_stream,
        write_stream,
        _,
    ):
        # Create a session using the client streams
        async with ClientSession(read_stream, write_stream) as session:
            yield session


@asynccontextmanager
async def get_sse_session(server_url: str):
    oauth_auth = OAuthClientProvider(
        server_url=server_url,
        client_metadata=OAuthClientMetadata(
            client_name="Example MCP Client",
            redirect_uris=[AnyUrl("http://localhost:3000/callback")],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            scope="user",
        ),
        storage=InMemoryTokenStorage(),
        redirect_handler=handle_redirect,
        callback_handler=handle_callback,
    )

    # Connect to a Server-Sent Events (SSE) server
    async with sse_client(
        url=server_url,
        auth=oauth_auth,
        timeout=60,
    ) as (read_stream, write_stream):
        # Create a session using the client streams
        async with ClientSession(read_stream, write_stream) as session:
            yield session


@asynccontextmanager
async def get_client_session_by_server(
    server_name: str, mcp_servers_config: MCPServersConfig
) -> AsyncGenerator[ClientSession, None]:
    # Find the server configuration by name
    server_config = mcp_servers_config.mcpServers.get(server_name)
    if not server_config:
        raise ValueError(f"Server '{server_name}' not found in configuration.")
    if isinstance(server_config, StdioServerConfig):
        async with get_stdio_session(
            StdioServerParameters(
                command=server_config.command,
                args=server_config.args or [],
                env=server_config.env,
            )
        ) as session:
            yield session
    elif isinstance(server_config, SSEServerConfig):
        async with get_sse_session(server_config.url) as session:
            yield session
    else:
        raise ValueError(f"Unsupported server type for '{server_name}': {type(server_config)}")
