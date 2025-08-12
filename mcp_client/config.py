from pydantic import BaseModel, Field, field_validator, model_validator


class BaseServerConfig(BaseModel):
    """Base configuration for MCP servers with common properties."""

    timeout: int | None = Field(default=60000, description="Timeout in milliseconds")

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v):
        if v is not None and v <= 0:
            raise ValueError("timeout must be a positive integer")
        return v


class StdioServerConfig(BaseServerConfig):
    """Configuration for stdio-based MCP servers."""

    type: str | None = Field(default="stdio", description="Server transport type")
    command: str = Field(..., description="Command to execute the server")
    args: list[str] | None = Field(default=None, description="Command line arguments")
    env: dict[str, str] | None = Field(
        default=None, description="Environment variables"
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v is not None and v != "stdio":
            raise ValueError('type must be "stdio" for StdioServerConfig')
        return v or "stdio"


class SSEServerConfig(BaseServerConfig):
    """Configuration for Server-Sent Events (SSE) based MCP servers."""

    type: str = Field(default="sse", description="Server transport type")
    url: str = Field(..., description="URL endpoint for the SSE server")
    headers: dict[str, str] | None = Field(default=None, description="HTTP headers")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v != "sse":
            raise ValueError('type must be "sse" for SSEServerConfig')
        return v


class MCPServersConfig(BaseModel):
    """Root configuration containing all MCP servers."""

    mcpServers: dict[str, StdioServerConfig | SSEServerConfig] = Field(
        ..., description="Dictionary of server name to server configuration"
    )

    @field_validator("mcpServers")
    @classmethod
    def validate_server_names(cls, v):
        for server_name in v.keys():
            if not server_name or len(server_name) > 250:
                raise ValueError(
                    "Server name must not be empty and must not be longer than 250 characters"
                )
        return v

    @model_validator(mode="before")
    @classmethod
    def validate_servers(cls, values):
        """Custom validation to handle server type discrimination."""
        if isinstance(values, dict):
            servers = values.get("mcpServers", {})
            validated_servers = {}

            for name, config in servers.items():
                if isinstance(config, dict):
                    server_type = config.get("type", "stdio")

                    if server_type == "sse":
                        validated_servers[name] = SSEServerConfig(**config)
                    else:
                        validated_servers[name] = StdioServerConfig(**config)
                else:
                    validated_servers[name] = config

            values["mcpServers"] = validated_servers
        return values
