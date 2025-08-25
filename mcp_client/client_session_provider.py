import webbrowser
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from mcp import ClientSession, StdioServerParameters
from mcp.client.auth import OAuthClientProvider
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import OAuthClientMetadata
from pydantic import AnyUrl

from auth_server import AuthServer
from util.terminal import display_hyperlink

from .mcp_logger import get_mcp_log_file
from .session_manager import get_session_manager

if TYPE_CHECKING:
    from state import State


async def handle_redirect(auth_url: str) -> None:
    print(f"ContextKit requires authorization, opening {display_hyperlink(auth_url)}")
    opened = webbrowser.open(auth_url)
    if not opened:
        print("Failed to open browser automatically. Please open the URL manually in your browser.")


async def handle_callback() -> tuple[str, str | None]:
    callback_url = input("Paste callback URL: ")
    params = parse_qs(urlparse(callback_url).query)
    return params["code"][0], params.get("state", [None])[0]


@asynccontextmanager
async def get_stdio_session(server_params: StdioServerParameters, config_dir: Path | None = None):
    with get_mcp_log_file(config_dir) as errlog:
        async with stdio_client(server_params, errlog=errlog) as (read, write):
            async with ClientSession(read, write) as session:
                yield session


@asynccontextmanager
async def get_streamablehttp_session(server_url: str, server_name: str, state: "State"):
    token_storage = state.get_token_storage(server_name)
    oauth_auth = OAuthClientProvider(
        server_url=server_url,
        client_metadata=OAuthClientMetadata(
            client_name="ContextKit MCP Client",
            redirect_uris=[AnyUrl("http://localhost:3000/callback")],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            scope="user",
        ),
        storage=token_storage,
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
async def get_sse_session(server_url: str, server_name: str, state: "State", auth_server: AuthServer | None = None):
    if auth_server is None:
        raise ValueError("AuthServer must be provided for SSE sessions")

    token_storage = state.get_token_storage(server_name)
    oauth_auth = OAuthClientProvider(
        server_url=server_url,
        client_metadata=OAuthClientMetadata(
            client_name="ContextKit MCP Client",
            redirect_uris=[AnyUrl(auth_server.callback_url)],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
        ),
        storage=token_storage,
        redirect_handler=handle_redirect,
        callback_handler=auth_server.handle_callback,
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
async def get_client_session_by_server(server_name: str) -> AsyncGenerator[ClientSession, None]:
    session_manager = get_session_manager()

    if session_manager.is_initialized:
        session = session_manager.get_session(server_name)
        yield session
