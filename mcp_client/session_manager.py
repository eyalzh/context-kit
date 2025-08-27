"""Session manager for pre-initialized MCP client sessions."""

import logging
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING

from mcp import ClientSession

from .config import HTTPServerConfig, SSEServerConfig, StdioServerConfig

if TYPE_CHECKING:
    from state import State


class MCPSessionManager:
    """Manages on-demand MCP client sessions."""

    def __init__(self):
        self._sessions: dict[str, ClientSession] = {}
        self._exit_stack: AsyncExitStack | None = None
        self._initialized = False
        self._state: State | None = None

    def set_state(self, state: "State") -> None:
        """Set the state for on-demand server initialization."""
        self._state = state
        # Initialize the exit stack for managing session lifecycles
        if self._exit_stack is None:
            self._exit_stack = AsyncExitStack()

    async def initialize_server(self, server_name: str) -> ClientSession:
        """Initialize a specific MCP server session on-demand."""
        if not self._state:
            raise RuntimeError("State not set. Call set_state() first.")

        if server_name in self._sessions:
            return self._sessions[server_name]

        if not self._state.mcp_config or not self._state.mcp_config.mcpServers:
            raise ValueError("No MCP servers configured")

        server_config = self._state.mcp_config.mcpServers.get(server_name)
        if not server_config:
            available_servers = list(self._state.mcp_config.mcpServers.keys())
            raise ValueError(f"Server '{server_name}' not found. Available servers: {available_servers}")

        if self._exit_stack is None:
            self._exit_stack = AsyncExitStack()

        try:
            logging.debug(f"Initializing on-demand session for server: {server_name}")

            if isinstance(server_config, StdioServerConfig):
                from mcp import StdioServerParameters

                from .client_session_provider import get_stdio_session

                session_cm = get_stdio_session(
                    StdioServerParameters(
                        command=server_config.command,
                        args=server_config.args or [],
                        env=server_config.env,
                    ),
                    config_dir=self._state.config_dir,
                )
            elif isinstance(server_config, SSEServerConfig):
                from auth_server import AuthServer

                from .client_session_provider import get_sse_session

                # Create a temporary auth server for this session
                auth_server = AuthServer()
                await self._exit_stack.enter_async_context(auth_server)
                session_cm = get_sse_session(server_config.url, server_name, self._state, auth_server)
            elif isinstance(server_config, HTTPServerConfig):
                from auth_server import AuthServer

                from .client_session_provider import get_streamablehttp_session

                # Create a temporary auth server for this session
                auth_server = AuthServer()
                await self._exit_stack.enter_async_context(auth_server)
                session_cm = get_streamablehttp_session(server_config, server_name, self._state, auth_server)
            else:
                raise ValueError(f"Unsupported server type for '{server_name}': {type(server_config)}")

            # Enter the session context manager and store the session
            session = await self._exit_stack.enter_async_context(session_cm)
            await session.initialize()
            self._sessions[server_name] = session

            logging.debug(f"Successfully initialized on-demand session for server: {server_name}")
            return session

        except Exception as e:
            logging.error(f"Failed to initialize MCP server '{server_name}': {e}")
            raise RuntimeError(f"Failed to initialize MCP server '{server_name}': {e}") from e

    async def initialize_all_sessions(self, state: "State") -> None:
        """Pre-initialize all MCP server sessions from config."""
        if self._initialized:
            return

        if not state.mcp_config or not state.mcp_config.mcpServers:
            logging.info("No MCP servers configured, skipping session initialization")
            return

        self._exit_stack = AsyncExitStack()

        logging.info(f"Initializing {len(state.mcp_config.mcpServers)} MCP server sessions...")

        # Use shared auth server for all SSE connections during initialization
        from auth_server import AuthServer

        async with AuthServer() as auth_server:
            for server_name, server_config in state.mcp_config.mcpServers.items():
                try:
                    logging.debug(f"Initializing session for server: {server_name}")

                    if isinstance(server_config, StdioServerConfig):
                        from mcp import StdioServerParameters

                        from .client_session_provider import get_stdio_session

                        session_cm = get_stdio_session(
                            StdioServerParameters(
                                command=server_config.command,
                                args=server_config.args or [],
                                env=server_config.env,
                            ),
                            config_dir=state.config_dir,
                        )
                    elif isinstance(server_config, SSEServerConfig):
                        from .client_session_provider import get_sse_session

                        session_cm = get_sse_session(server_config.url, server_name, state, auth_server)
                    elif isinstance(server_config, HTTPServerConfig):
                        from .client_session_provider import get_streamablehttp_session

                        session_cm = get_streamablehttp_session(server_config, server_name, state, auth_server)
                    else:
                        raise ValueError(f"Unsupported server type for '{server_name}': {type(server_config)}")

                    # Enter the session context manager and store the session
                    session = await self._exit_stack.enter_async_context(session_cm)
                    await session.initialize()
                    self._sessions[server_name] = session

                    logging.debug(f"Successfully initialized session for server: {server_name}")

                except Exception as e:
                    logging.error(f"Failed to initialize MCP server '{server_name}': {e}")
                    await self.cleanup()
                    raise RuntimeError(f"Failed to initialize MCP server '{server_name}': {e}") from e

        self._initialized = True
        logging.info(f"Successfully initialized {len(self._sessions)} MCP server sessions")

    def get_session(self, server_name: str) -> ClientSession:
        """Get a session by server name, initializing on-demand if needed."""
        session = self._sessions.get(server_name)
        if session:
            return session

        # Session not found, this indicates it needs to be initialized on-demand
        # For backwards compatibility, raise error if session manager was initialized with old method
        if self._initialized and not self._state:
            available_servers = list(self._sessions.keys())
            raise ValueError(f"Server '{server_name}' not found. Available servers: {available_servers}")

        # For on-demand initialization, we cannot initialize synchronously
        # The caller should use get_session_async instead
        raise RuntimeError(
            f"Session for '{server_name}' not initialized. Use get_session_async() or initialize_server() first."
        )

    async def get_session_async(self, server_name: str) -> ClientSession:
        """Get a session by server name, initializing on-demand if needed."""
        session = self._sessions.get(server_name)
        if session:
            return session

        # Initialize the server on-demand
        return await self.initialize_server(server_name)

    async def cleanup(self) -> None:
        """Clean up all sessions and resources."""
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception as e:
                logging.error(f"Error during session cleanup: {e}")
            finally:
                self._exit_stack = None

        self._sessions.clear()
        self._initialized = False
        logging.debug("MCP session manager cleaned up")

    @property
    def is_initialized(self) -> bool:
        """Check if the session manager is initialized."""
        return self._initialized

    @property
    def server_names(self) -> list[str]:
        """Get list of available server names (both initialized and configured)."""
        if self._state and self._state.mcp_config and self._state.mcp_config.mcpServers:
            return list(self._state.mcp_config.mcpServers.keys())
        return list(self._sessions.keys())


# Global session manager instance
_session_manager = MCPSessionManager()


def get_session_manager() -> MCPSessionManager:
    """Get the global session manager instance."""
    return _session_manager
