import json
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestCLI:
    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary git repository for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Initialize git repo
            subprocess.run(
                ["git", "init"], cwd=repo_path, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"], cwd=repo_path, check=True
            )

            # Create initial commit
            (repo_path / "README.md").write_text("Test repo")
            subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True
            )

            yield repo_path

    @pytest.fixture
    def temp_non_git_dir(self):
        """Create a temporary directory that is NOT a git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def run_cli(self, args, cwd=None):
        """Run the CLI and return result."""
        # Get the path to cxk.py relative to this test file
        cli_path = Path(__file__).parent.parent.parent / "cxk.py"
        cmd = ["python", str(cli_path)] + args

        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        return result

    def test_init_in_git_repo(self, temp_git_repo):
        """Test 'cxk init' in a git repository."""
        result = self.run_cli(["init"], cwd=temp_git_repo)

        assert result.returncode == 0
        assert "ContextKit project initialized successfully!" in result.stdout

        # Check that .cxk directory and mcp.json were created
        cxk_dir = temp_git_repo / ".cxk"
        assert cxk_dir.exists()
        assert cxk_dir.is_dir()

        mcp_json = cxk_dir / "mcp.json"
        assert mcp_json.exists()

        # Verify mcp.json content
        with open(mcp_json) as f:
            config = json.load(f)
        assert "mcpServers" in config
        assert config["mcpServers"] == {}

    def test_init_outside_git_repo(self, temp_non_git_dir):
        """Test 'cxk init' outside a git repository should fail."""
        result = self.run_cli(["init"], cwd=temp_non_git_dir)

        assert result.returncode != 0
        assert "Must be run from within a git repository" in result.stderr

    def test_init_already_initialized(self, temp_git_repo):
        """Test 'cxk init' when already initialized."""
        # Initialize first time
        result1 = self.run_cli(["init"], cwd=temp_git_repo)
        assert result1.returncode == 0

        # Initialize second time
        result2 = self.run_cli(["init"], cwd=temp_git_repo)
        assert result2.returncode == 0
        assert "Project is already initialized!" in result2.stdout

    def test_mcp_before_init(self, temp_git_repo):
        """Test MCP commands before initialization should fail."""
        result = self.run_cli(
            ["mcp", "add-sse", "test-server", "http://example.com"], cwd=temp_git_repo
        )

        assert result.returncode != 0
        assert "Project not initialized. Run 'cxk init' first." in result.stderr

    def test_mcp_add_sse(self, temp_git_repo):
        """Test adding an SSE MCP server."""
        # Initialize project first
        init_result = self.run_cli(["init"], cwd=temp_git_repo)
        assert init_result.returncode == 0

        # Add SSE server
        result = self.run_cli(
            ["mcp", "add-sse", "test-sse", "http://example.com/sse"], cwd=temp_git_repo
        )

        assert result.returncode == 0
        assert (
            "Added SSE server 'test-sse' with URL: http://example.com/sse"
            in result.stdout
        )

        # Verify server was added to config
        mcp_json = temp_git_repo / ".cxk" / "mcp.json"
        with open(mcp_json) as f:
            config = json.load(f)

        assert "test-sse" in config["mcpServers"]
        server_config = config["mcpServers"]["test-sse"]
        assert server_config["type"] == "sse"
        assert server_config["url"] == "http://example.com/sse"

    def test_mcp_add_stdio_simple(self, temp_git_repo):
        """Test adding a simple stdio MCP server."""
        # Initialize project first
        init_result = self.run_cli(["init"], cwd=temp_git_repo)
        assert init_result.returncode == 0

        # Add stdio server
        result = self.run_cli(
            ["mcp", "add-stdio", "test-stdio", "--", "python", "-m", "server"],
            cwd=temp_git_repo,
        )

        assert result.returncode == 0
        assert (
            "Added stdio server 'test-stdio' with command: python -m server"
            in result.stdout
        )

        # Verify server was added to config
        mcp_json = temp_git_repo / ".cxk" / "mcp.json"
        with open(mcp_json) as f:
            config = json.load(f)

        assert "test-stdio" in config["mcpServers"]
        server_config = config["mcpServers"]["test-stdio"]
        assert server_config["type"] == "stdio"
        assert server_config["command"] == "python"
        assert server_config["args"] == ["-m", "server"]

    def test_mcp_add_stdio_with_env(self, temp_git_repo):
        """Test adding a stdio MCP server with environment variables."""
        # Initialize project first
        init_result = self.run_cli(["init"], cwd=temp_git_repo)
        assert init_result.returncode == 0

        # Add stdio server with env vars
        result = self.run_cli(
            [
                "mcp",
                "add-stdio",
                "test-stdio-env",
                "--env",
                "API_KEY=test123",
                "--env",
                "DEBUG=true",
                "--",
                "node",
                "server.js",
            ],
            cwd=temp_git_repo,
        )

        assert result.returncode == 0
        assert (
            "Added stdio server 'test-stdio-env' with command: node server.js"
            in result.stdout
        )
        assert (
            "Environment variables: {'API_KEY': 'test123', 'DEBUG': 'true'}"
            in result.stdout
        )

        # Verify server was added to config
        mcp_json = temp_git_repo / ".cxk" / "mcp.json"
        with open(mcp_json) as f:
            config = json.load(f)

        assert "test-stdio-env" in config["mcpServers"]
        server_config = config["mcpServers"]["test-stdio-env"]
        assert server_config["type"] == "stdio"
        assert server_config["command"] == "node"
        assert server_config["args"] == ["server.js"]
        assert server_config["env"] == {"API_KEY": "test123", "DEBUG": "true"}

    def test_mcp_add_http_placeholder(self, temp_git_repo):
        """Test adding HTTP MCP server (placeholder functionality)."""
        # Initialize project first
        init_result = self.run_cli(["init"], cwd=temp_git_repo)
        assert init_result.returncode == 0

        # Add HTTP server (should show placeholder message)
        result = self.run_cli(
            ["mcp", "add-http", "test-http", "http://example.com/api"],
            cwd=temp_git_repo,
        )

        assert result.returncode == 0
        assert (
            "HTTP server support not implemented yet. Would add 'test-http' with URL: http://example.com/api"
            in result.stdout
        )

    def test_mcp_duplicate_server_name(self, temp_git_repo):
        """Test adding MCP server with duplicate name should fail."""
        # Initialize project first
        init_result = self.run_cli(["init"], cwd=temp_git_repo)
        assert init_result.returncode == 0

        # Add first server
        result1 = self.run_cli(
            ["mcp", "add-sse", "duplicate", "http://example.com/1"], cwd=temp_git_repo
        )
        assert result1.returncode == 0

        # Try to add server with same name
        result2 = self.run_cli(
            ["mcp", "add-sse", "duplicate", "http://example.com/2"], cwd=temp_git_repo
        )
        assert result2.returncode != 0
        assert "Server 'duplicate' already exists" in result2.stderr

    def test_invalid_env_format(self, temp_git_repo):
        """Test stdio command with invalid environment variable format."""
        # Initialize project first
        init_result = self.run_cli(["init"], cwd=temp_git_repo)
        assert init_result.returncode == 0

        # Try to add stdio server with invalid env format
        result = self.run_cli(
            [
                "mcp",
                "add-stdio",
                "test-stdio",
                "--env",
                "INVALID_FORMAT",
                "--",
                "python",
                "server.py",
            ],
            cwd=temp_git_repo,
        )

        assert result.returncode != 0
        assert (
            "Invalid environment variable format: INVALID_FORMAT. Use KEY=VALUE format."
            in result.stderr
        )

    def test_mcp_add_server_preserves_existing(self, temp_git_repo):
        """Test that adding a new server preserves existing servers."""
        # Initialize project first
        init_result = self.run_cli(["init"], cwd=temp_git_repo)
        assert init_result.returncode == 0

        # Add first server
        result1 = self.run_cli(
            ["mcp", "add-sse", "server1", "http://example.com/1"], cwd=temp_git_repo
        )
        assert result1.returncode == 0

        # Add second server
        result2 = self.run_cli(
            ["mcp", "add-stdio", "server2", "--", "python", "server.py"], cwd=temp_git_repo
        )
        assert result2.returncode == 0

        # Verify both servers exist in config
        mcp_json = temp_git_repo / ".cxk" / "mcp.json"
        with open(mcp_json) as f:
            config = json.load(f)

        # Both servers should be present
        assert "server1" in config["mcpServers"]
        assert "server2" in config["mcpServers"]

        # Verify server1 config is preserved
        server1_config = config["mcpServers"]["server1"]
        assert server1_config["type"] == "sse"
        assert server1_config["url"] == "http://example.com/1"

        # Verify server2 config
        server2_config = config["mcpServers"]["server2"]
        assert server2_config["type"] == "stdio"
        assert server2_config["command"] == "python"
        assert server2_config["args"] == ["server.py"]

    def test_cli_help(self):
        """Test CLI help output."""
        result = self.run_cli(["--help"])
        assert result.returncode == 0
        assert "ContextKit CLI tool" in result.stdout
        assert "init" in result.stdout
        assert "mcp" in result.stdout
        assert "create-spec" in result.stdout

    def test_create_spec_with_variables(self, temp_non_git_dir):
        """Test create-spec with a template containing variables."""
        # Create a test template with variables
        template_content = """
Hello {{ name }}!
Your age is {{ age }} and you live in {{ city }}.
Today's weather is {{ weather.condition }} with temperature {{ weather.temp }}.
"""
        template_file = temp_non_git_dir / "test_template.j2"
        template_file.write_text(template_content)

        # Run create-spec command
        result = self.run_cli(["create-spec", str(template_file)])

        assert result.returncode == 0
        assert "Template variables:" in result.stdout
        assert "- age" in result.stdout
        assert "- city" in result.stdout
        assert "- name" in result.stdout
        assert "- weather" in result.stdout

    def test_create_spec_no_variables(self, temp_non_git_dir):
        """Test create-spec with a template containing no variables."""
        # Create a test template without variables
        template_content = "This is a static template with no variables."
        template_file = temp_non_git_dir / "static_template.j2"
        template_file.write_text(template_content)

        # Run create-spec command
        result = self.run_cli(["create-spec", str(template_file)])

        assert result.returncode == 0
        assert "No variables found in template" in result.stdout

    def test_create_spec_relative_path(self, temp_non_git_dir):
        """Test create-spec with a relative path (filename only)."""
        # Create a test template
        template_content = "Hello {{ username }}!"
        template_file = temp_non_git_dir / "relative_template.j2"
        template_file.write_text(template_content)

        # Run create-spec command with just the filename (relative path)
        result = self.run_cli(["create-spec", "relative_template.j2"], cwd=temp_non_git_dir)

        assert result.returncode == 0
        assert "Template variables:" in result.stdout
        assert "- username" in result.stdout

    def test_create_spec_file_not_found(self, temp_non_git_dir):
        """Test create-spec with non-existent template file."""
        result = self.run_cli(["create-spec", "non_existent.j2"], cwd=temp_non_git_dir)

        assert result.returncode != 0
        assert "Error: Template file 'non_existent.j2' not found" in result.stderr

    def test_create_spec_invalid_template(self, temp_non_git_dir):
        """Test create-spec with invalid template syntax."""
        # Create a template with invalid Jinja2 syntax
        template_content = "Hello {{ name with invalid syntax!"
        template_file = temp_non_git_dir / "invalid_template.j2"
        template_file.write_text(template_content)

        # Run create-spec command
        result = self.run_cli(["create-spec", str(template_file)])

        assert result.returncode != 0
