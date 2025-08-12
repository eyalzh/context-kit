import json
from pathlib import Path

from mcp_client.config import MCPServersConfig


class State:
    def __init__(self):
        self.project_root = self._find_git_root()
        self.config_dir = self.project_root / ".cxk" if self.project_root else None
        self.config_file = self.config_dir / "mcp.json" if self.config_dir else None
        self._mcp_config: MCPServersConfig | None = None

    def _find_git_root(self) -> Path | None:
        current = Path.cwd()
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        return None

    @property
    def is_in_git_repo(self) -> bool:
        return self.project_root is not None

    @property
    def is_initialized(self) -> bool:
        return self.config_file is not None and self.config_file.exists()

    @property
    def mcp_config(self) -> MCPServersConfig:
        if self._mcp_config is None:
            self._load_mcp_config()
        return self._mcp_config or MCPServersConfig(mcpServers={})

    def _load_mcp_config(self):
        if not self.is_initialized:
            self._mcp_config = MCPServersConfig(mcpServers={})
            return

        try:
            if self.config_file:
                with open(self.config_file) as f:
                    data = json.load(f)
                    self._mcp_config = MCPServersConfig(**data)
        except (json.JSONDecodeError, FileNotFoundError, Exception):
            self._mcp_config = MCPServersConfig(mcpServers={})

    def save_mcp_config(self):
        if not self.config_dir:
            raise RuntimeError("Not in a git repository")

        self.config_dir.mkdir(exist_ok=True)
        if self.config_file:
            with open(self.config_file, "w") as f:
                json.dump(
                    self.mcp_config.model_dump(exclude_none=True),
                    f,
                    indent=2,
                )

    def initialize_project(self):
        if not self.is_in_git_repo:
            raise RuntimeError("Must be run from within a git repository")

        if self.config_dir:
            self.config_dir.mkdir(exist_ok=True)
        if self.config_file and not self.config_file.exists():
            self.save_mcp_config()
