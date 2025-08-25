"""Session manager for pre-initialized MCP client sessions."""

import logging
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING

from mcp import ClientSession

from .config import SSEServerConfig, StdioServerConfig

if TYPE_CHECKING:
    from state import State


class MCPSessionManager:
    """Manages pre-initialized MCP client sessions."""

    def __init__(self):
        self._sessions: dict[str, ClientSession] = {}
        self._exit_stack: AsyncExitStack | None = None
        self._initialized = False

    async def initialize_all_sessions(self, state: "State") -> None:
        """Pre-initialize all MCP server sessions from config."""
        if self._initialized:
            return

        if not state.mcp_config or not state.mcp_config.mcpServers:
            logging.info("No MCP servers configured, skipping session initialization")
            return

        self._exit_stack = AsyncExitStack()

        logging.info(f"Initializing {len(state.mcp_config.mcpServers)} MCP server sessions...")

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

                    session_cm = get_sse_session(server_config.url, server_name, state)
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
        """Get a pre-initialized session by server name."""
        if not self._initialized:
            raise RuntimeError("Session manager not initialized. Call initialize_all_sessions() first.")

        session = self._sessions.get(server_name)
        if not session:
            available_servers = list(self._sessions.keys())
            raise ValueError(f"Server '{server_name}' not found. Available servers: {available_servers}")

        return session

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
        """Get list of initialized server names."""
        return list(self._sessions.keys())


# Global session manager instance
_session_manager = MCPSessionManager()


def get_session_manager() -> MCPSessionManager:
    """Get the global session manager instance."""
    return _session_manager
