"""OAuth2 authentication server for handling MCP client callbacks."""

import asyncio
import logging
import threading

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse


class AuthServer:
    """FastAPI-based OAuth2 callback server for MCP authentication."""

    def __init__(self, host: str = "localhost", port: int = 41008):
        """Initialize the auth server."""
        self.host = host
        self.port = port
        self.app = FastAPI()
        self.server: uvicorn.Server | None = None
        self.server_thread: threading.Thread | None = None

        # Storage for the callback response
        self._callback_future: asyncio.Future | None = None
        self._callback_code: str | None = None
        self._callback_state: str | None = None
        self._main_loop: asyncio.AbstractEventLoop | None = None

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes."""

        @self.app.get("/callback")
        async def callback_endpoint(request: Request):
            """Handle OAuth2 callback."""
            query_params = dict(request.query_params)

            # Extract code and state from query parameters
            code = query_params.get("code")
            state = query_params.get("state")
            error = query_params.get("error")

            if error:
                error_description = query_params.get("error_description", "Unknown error")
                if self._callback_future and not self._callback_future.done():
                    # Schedule the exception in the main event loop
                    if self._main_loop:
                        self._main_loop.call_soon_threadsafe(
                            self._callback_future.set_exception,
                            Exception(f"OAuth error: {error} - {error_description}"),
                        )
                return HTMLResponse(
                    content=f"<html><body><h2>Authentication Error</h2><p>{error}: {error_description}</p></body></html>",  # noqa: E501
                    status_code=400,
                )

            if not code:
                if self._callback_future and not self._callback_future.done():
                    # Schedule the exception in the main event loop
                    if self._main_loop:
                        self._main_loop.call_soon_threadsafe(
                            self._callback_future.set_exception, Exception("No authorization code received")
                        )
                return HTMLResponse(
                    content="<html><body><h2>Error</h2><p>No authorization code received</p></body></html>",
                    status_code=400,
                )

            # Store the callback data
            self._callback_code = code
            self._callback_state = state

            # Signal that callback was received
            if self._callback_future and not self._callback_future.done():
                # Schedule the future resolution in the main event loop
                if self._main_loop:
                    self._main_loop.call_soon_threadsafe(self._callback_future.set_result, (code, state))
                    logging.info("OAuth2 callback handled successfully")
                else:
                    logging.error("Main event loop is not set; cannot set callback future result")
            else:
                logging.error("Callback future is not set or already done; cannot set result")

            return HTMLResponse(
                content="""
                <html>
                <body>
                    <h2>Authorization Successful</h2>
                    <p>You have successfully authorized the MCP client. You can now close this window.</p>
                </body>
                </html>
                """
            )

    async def start(self):
        """Start the auth server in a background thread."""
        logging.info(f"Starting auth server at http://{self.host}:{self.port}")
        if self.server_thread and self.server_thread.is_alive():
            logging.info("Auth server is already running")
            return  # Already running

        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="warning",  # Reduce log noise
            access_log=False,
        )
        self.server = uvicorn.Server(config)

        # Start server in a separate thread to avoid blocking
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

        # Wait a bit for the server to start
        await asyncio.sleep(0.1)

    def _run_server(self):
        """Run the server in the thread."""
        if self.server is not None:
            asyncio.run(self.server.serve())

    async def handle_callback(self) -> tuple[str, str | None]:
        """
        Wait for and handle the OAuth2 callback.

        Returns:
            tuple: (code, state) from the OAuth2 callback

        Raises:
            Exception: If there's an error in the OAuth2 flow
        """
        # Capture the current event loop
        self._main_loop = asyncio.get_running_loop()

        # Create a future to wait for the callback
        self._callback_future = asyncio.Future()

        try:
            # Wait for the callback to be received
            logging.info("Waiting for OAuth2 callback...")
            code, state = await self._callback_future
            logging.info(f"Received callback with code: {code}, state: {state}")
            return code, state
        finally:
            # Clean up
            logging.info("Cleaning up auth server state after callback")
            self._callback_future = None
            self._main_loop = None

    async def stop(self):
        """Stop the auth server and clean up state."""
        if self.server:
            self.server.should_exit = True

        if self.server_thread and self.server_thread.is_alive():
            # Wait a bit for graceful shutdown
            self.server_thread.join(timeout=1.0)

        # Clear state
        self._callback_code = None
        self._callback_state = None
        self._callback_future = None
        self._main_loop = None
        self.server = None
        self.server_thread = None

        logging.info("Auth server stopped")

    @property
    def callback_url(self) -> str:
        """Get the callback URL for this auth server."""
        return f"http://{self.host}:{self.port}/callback"

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
        return None
