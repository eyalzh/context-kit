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
            subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)

            # Create initial commit
            (repo_path / "README.md").write_text("Test repo")
            subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True)

            yield repo_path

    @pytest.fixture
    def temp_non_git_dir(self):
        """Create a temporary directory that is NOT a git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def run_cli(self, args, cwd=None, use_test_runner=False, input: str | None = None):
        """Run the CLI and return result."""
        if use_test_runner:
            # Use test runner that patches collect_var_value
            cli_path = Path(__file__).parent.parent / "test_runner.py"
        else:
            # Get the path to cxk.py relative to this test file
            cli_path = Path(__file__).parent.parent.parent / "cxk.py"

        cmd = ["python", str(cli_path)] + args

        result = subprocess.run(cmd, cwd=cwd, input=input, capture_output=True, text=True)
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
        result = self.run_cli(["mcp", "add-sse", "test-server", "http://example.com"], cwd=temp_git_repo)

        assert result.returncode != 0
        assert "Project not initialized. Run 'cxk init' first." in result.stderr

    def test_mcp_add_sse(self, temp_git_repo):
        """Test adding an SSE MCP server."""
        # Initialize project first
        init_result = self.run_cli(["init"], cwd=temp_git_repo)
        assert init_result.returncode == 0

        # Add SSE server
        result = self.run_cli(["mcp", "add-sse", "test-sse", "http://example.com/sse"], cwd=temp_git_repo)

        assert result.returncode == 0
        assert "Added SSE server 'test-sse' with URL: http://example.com/sse" in result.stdout

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
        assert "Added stdio server 'test-stdio' with command: python -m server" in result.stdout

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
        assert "Added stdio server 'test-stdio-env' with command: node server.js" in result.stdout
        assert "Environment variables: {'API_KEY': 'test123', 'DEBUG': 'true'}" in result.stdout

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
        result1 = self.run_cli(["mcp", "add-sse", "duplicate", "http://example.com/1"], cwd=temp_git_repo)
        assert result1.returncode == 0

        # Try to add server with same name
        result2 = self.run_cli(["mcp", "add-sse", "duplicate", "http://example.com/2"], cwd=temp_git_repo)
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
        assert "Invalid environment variable format: INVALID_FORMAT. Use KEY=VALUE format." in result.stderr

    def test_mcp_add_server_preserves_existing(self, temp_git_repo):
        """Test that adding a new server preserves existing servers."""
        # Initialize project first
        init_result = self.run_cli(["init"], cwd=temp_git_repo)
        assert init_result.returncode == 0

        # Add first server
        result1 = self.run_cli(["mcp", "add-sse", "server1", "http://example.com/1"], cwd=temp_git_repo)
        assert result1.returncode == 0

        # Add second server
        result2 = self.run_cli(["mcp", "add-stdio", "server2", "--", "python", "server.py"], cwd=temp_git_repo)
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

        # Run create-spec command with test runner to patch collect_var_value
        result = self.run_cli(["create-spec", "--verbose", str(template_file)], use_test_runner=True)

        assert result.returncode == 0

        # Verify rendered template output
        assert "Hello John!" in result.stdout
        assert "Your age is 25 and you live in New York." in result.stdout
        assert "Today's weather is sunny with temperature 75F." in result.stdout

    def test_create_spec_no_variables(self, temp_non_git_dir):
        """Test create-spec with a template containing no variables."""
        # Create a test template without variables
        template_content = "This is a static template with no variables."
        template_file = temp_non_git_dir / "static_template.j2"
        template_file.write_text(template_content)

        # Run create-spec command with test runner (patching won't affect this case)
        result = self.run_cli(["create-spec", "--verbose", str(template_file)], use_test_runner=True)

        assert result.returncode == 0
        assert "No variables found in template" in result.stderr

        # Verify rendered template output for static template
        assert "This is a static template with no variables." in result.stdout

    def test_create_spec_relative_path(self, temp_non_git_dir):
        """Test create-spec with a relative path (filename only)."""
        # Create a test template
        template_content = "Hello {{ username }}!"
        template_file = temp_non_git_dir / "relative_template.j2"
        template_file.write_text(template_content)

        # Run create-spec command with just the filename (relative path) using test runner
        result = self.run_cli(
            ["create-spec", "--verbose", "relative_template.j2"], cwd=temp_non_git_dir, use_test_runner=True
        )

        assert result.returncode == 0
        assert "username: testuser" in result.stderr

        # Verify rendered template output
        assert "Hello testuser!" in result.stdout

    def test_create_spec_file_not_found(self, temp_non_git_dir):
        """Test create-spec with non-existent template file."""
        result = self.run_cli(["create-spec", "non_existent.j2"], cwd=temp_non_git_dir, use_test_runner=True)

        assert result.returncode != 0
        assert "Error: Template file 'non_existent.j2' not found" in result.stderr

    def test_create_spec_invalid_template(self, temp_non_git_dir):
        """Test create-spec with invalid template syntax."""
        # Create a template with invalid Jinja2 syntax
        template_content = "Hello {{ name with invalid syntax!"
        template_file = temp_non_git_dir / "invalid_template.j2"
        template_file.write_text(template_content)

        # Run create-spec command with test runner
        result = self.run_cli(["create-spec", str(template_file)], use_test_runner=True)

        assert result.returncode != 0

    def test_create_spec_with_output_file(self, temp_non_git_dir):
        """Test create-spec with --output flag saves to file."""
        # Create a test template with variables
        template_content = """Hello {{ name }}!
Your age is {{ age }} and you live in {{ city }}."""
        template_file = temp_non_git_dir / "output_test_template.j2"
        template_file.write_text(template_content)

        # Define output file
        output_file = temp_non_git_dir / "rendered_spec.md"

        # Run create-spec command with --output flag
        result = self.run_cli(
            ["create-spec", "--verbose", str(template_file), "--output", str(output_file)], use_test_runner=True
        )

        assert result.returncode == 0

        # Verify file was created and contains expected content
        assert output_file.exists()
        content = output_file.read_text()
        assert "Hello John!" in content
        assert "Your age is 25 and you live in New York." in content

    def test_create_spec_output_file_relative_path(self, temp_non_git_dir):
        """Test create-spec with --output using relative path."""
        # Create a test template
        template_content = "Template for {{ username }}"
        template_file = temp_non_git_dir / "relative_output_template.j2"
        template_file.write_text(template_content)

        # Run create-spec command with relative output path
        result = self.run_cli(
            ["create-spec", "--verbose", str(template_file), "--output", "output.md"],
            cwd=temp_non_git_dir,
            use_test_runner=True,
        )

        assert result.returncode == 0

        # Verify file was created with absolute path in message
        output_file = temp_non_git_dir / "output.md"
        assert output_file.exists()
        assert "Template for testuser" in output_file.read_text()

    def test_create_spec_stdout_vs_file_output(self, temp_non_git_dir):
        """Test that stdout and file output contain the same content."""
        # Create a test template
        template_content = "Hello {{ name }}! You are {{ age }} years old."
        template_file = temp_non_git_dir / "comparison_template.j2"
        template_file.write_text(template_content)

        # Run without --output (stdout)
        result_stdout = self.run_cli(["create-spec", "--verbose", str(template_file)], use_test_runner=True)

        # Extract rendered content from stdout
        stdout_lines = result_stdout.stdout.split("\n")
        rendered_start = False
        stdout_content = []
        for line in stdout_lines:
            if line == "Rendered template:":
                rendered_start = True
                continue
            elif rendered_start:
                stdout_content.append(line)

        # If we found a "Rendered template:" marker, use content after it
        if stdout_content:
            stdout_rendered = "\n".join(stdout_content).strip()
        else:
            # If no marker found, assume the entire output is the rendered template
            # (skip logging messages that contain colons)
            template_lines = [
                line
                for line in stdout_lines
                if ":" not in line or not line.strip().startswith(("Collecting", "name:", "age:", "city:"))
            ]
            stdout_rendered = "\n".join(template_lines).strip()

        # Run with --output (file)
        output_file = temp_non_git_dir / "comparison_output.md"
        result_file = self.run_cli(
            ["create-spec", "--verbose", str(template_file), "--output", str(output_file)], use_test_runner=True
        )

        assert result_stdout.returncode == 0
        assert result_file.returncode == 0

        # Compare content
        file_content = output_file.read_text().strip()
        assert stdout_rendered == file_content
        assert "Hello John! You are 25 years old." in file_content

    def test_create_spec_with_var_override_single(self, temp_non_git_dir):
        """Test create-spec with single --var override."""
        # Create a test template with variables
        template_content = "Hello {{ name }}! You are {{ age }} years old."
        template_file = temp_non_git_dir / "var_override_template.j2"
        template_file.write_text(template_content)

        # Run create-spec command with --var override
        result = self.run_cli(
            ["create-spec", "--verbose", str(template_file), "--var", "name=Alice"], use_test_runner=True
        )

        assert result.returncode == 0

        # Verify rendered template output
        assert "Hello Alice! You are 25 years old." in result.stdout

    def test_create_spec_with_var_override_multiple(self, temp_non_git_dir):
        """Test create-spec with multiple --var overrides."""
        # Create a test template with variables
        template_content = "Hello {{ name }}! You are {{ age }} years old and live in {{ city }}."
        template_file = temp_non_git_dir / "multiple_var_override_template.j2"
        template_file.write_text(template_content)

        # Run create-spec command with multiple --var overrides
        result = self.run_cli(
            ["create-spec", "--verbose", str(template_file), "--var", "name=Bob", "--var", "city=Boston"],
            use_test_runner=True,
        )

        assert result.returncode == 0

        # Verify rendered template output
        assert "Hello Bob! You are 25 years old and live in Boston." in result.stdout

    def test_create_spec_with_var_override_all_variables(self, temp_non_git_dir):
        """Test create-spec with all variables provided via --var (no interactive prompts)."""
        # Create a test template with variables
        template_content = "{{ greeting }} {{ name }}! Your score is {{ score }}."
        template_file = temp_non_git_dir / "all_var_override_template.j2"
        template_file.write_text(template_content)

        # Run create-spec command with all variables provided
        result = self.run_cli(
            [
                "create-spec",
                "--verbose",
                str(template_file),
                "--var",
                "greeting=Hi",
                "--var",
                "name=Charlie",
                "--var",
                "score=100",
            ],
            use_test_runner=True,
        )

        assert result.returncode == 0

        # Verify rendered template output
        assert "Hi Charlie! Your score is 100." in result.stdout

    def test_create_spec_with_var_override_json_value(self, temp_non_git_dir):
        """Test create-spec with --var containing JSON value."""
        # Create a test template with JSON variable
        template_content = "User: {{ user.name }}, Email: {{ user.email }}"
        template_file = temp_non_git_dir / "json_var_override_template.j2"
        template_file.write_text(template_content)

        # Run create-spec command with JSON --var
        json_value = '{"name": "Dave", "email": "dave@example.com"}'
        result = self.run_cli(
            ["create-spec", "--verbose", str(template_file), "--var", f"user={json_value}"], use_test_runner=True
        )

        assert result.returncode == 0

        # Verify rendered template output
        assert "User: Dave, Email: dave@example.com" in result.stdout

    def test_create_spec_with_var_invalid_format(self, temp_non_git_dir):
        """Test create-spec with invalid --var format."""
        # Create a test template
        template_content = "Hello {{ name }}!"
        template_file = temp_non_git_dir / "invalid_var_format_template.j2"
        template_file.write_text(template_content)

        # Run create-spec command with invalid --var format (missing =)
        result = self.run_cli(
            ["create-spec", "--verbose", str(template_file), "--var", "invalid_format"], use_test_runner=True
        )

        assert result.returncode != 0
        assert "Error: Invalid variable format 'invalid_format'. Use KEY=VALUE format." in result.stderr

    def test_create_spec_with_var_equals_in_value(self, temp_non_git_dir):
        """Test create-spec with --var value containing equals sign."""
        # Create a test template
        template_content = "Equation: {{ equation }}"
        template_file = temp_non_git_dir / "equals_in_value_template.j2"
        template_file.write_text(template_content)

        # Run create-spec command with --var value containing equals
        result = self.run_cli(
            ["create-spec", "--verbose", str(template_file), "--var", "equation=x=y+z"], use_test_runner=True
        )

        assert result.returncode == 0

        # Verify rendered template output
        assert "Equation: x=y+z" in result.stdout

    def test_create_spec_with_var_and_output_file(self, temp_non_git_dir):
        """Test create-spec with --var and --output together."""
        # Create a test template
        template_content = "Project: {{ project }}, Version: {{ version }}"
        template_file = temp_non_git_dir / "var_and_output_template.j2"
        template_file.write_text(template_content)

        # Define output file
        output_file = temp_non_git_dir / "var_output.md"

        # Run create-spec command with both --var and --output
        result = self.run_cli(
            [
                "create-spec",
                "--verbose",
                str(template_file),
                "--var",
                "project=MyApp",
                "--var",
                "version=1.0.0",
                "--output",
                str(output_file),
            ],
            use_test_runner=True,
        )

        assert result.returncode == 0
        assert f"Rendered template saved to: {output_file}" in result.stderr

        # Verify file was created and contains expected content
        assert output_file.exists()
        content = output_file.read_text()
        assert "Project: MyApp, Version: 1.0.0" in content

    def test_create_spec_pipe_mode(self, temp_non_git_dir):
        """Test create-spec with stdin pipe mode (no template file argument)."""
        # Template content to pipe via stdin
        template_content = (
            "# Task Template\n\n## Ticket description\n\n{{ ticket.id }}\n\n{{ ticket.description }}\n\n"
            "## Additional context\n\n{{ additional_context }}"
        )

        # Run create-spec command without template file argument, piping template via stdin
        result = self.run_cli(
            [
                "create-spec",
                "--verbose",
                "--var",
                'ticket={"id":1}',
                "--var",
                "additional_context=test context",
            ],
            cwd=temp_non_git_dir,
            input=template_content,
        )

        assert result.returncode == 0

        # Verify rendered template output contains expected content
        assert "# Task Template" in result.stdout
        assert "## Ticket description" in result.stdout
        assert "1" in result.stdout  # ticket.id
        assert "## Additional context" in result.stdout
        assert "test context" in result.stdout

    def test_create_spec_pipe_mode_with_output_file(self, temp_non_git_dir):
        """Test create-spec with stdin pipe mode and --output flag."""
        # Template content to pipe via stdin
        template_content = "Piped template: {{ message }}"

        # Define output file
        output_file = temp_non_git_dir / "piped_output.md"

        # Run create-spec command with stdin and --output
        result = self.run_cli(
            [
                "create-spec",
                "--verbose",
                "--var",
                "message=Hello from pipe!",
                "--output",
                str(output_file),
            ],
            cwd=temp_non_git_dir,
            input=template_content,
        )

        assert result.returncode == 0
        assert f"Rendered template saved to: {output_file}" in result.stderr

        # Verify file was created and contains expected content
        assert output_file.exists()
        content = output_file.read_text()
        assert "Piped template: Hello from pipe!" in content

    def test_create_spec_with_mcp_call(self, temp_git_repo):
        """Test create-spec with template that includes MCP tool calls."""
        # Initialize project first
        init_result = self.run_cli(["init"], cwd=temp_git_repo)
        assert init_result.returncode == 0

        # Add test MCP server
        server_path = Path(__file__).parent.parent / "mcp_test_server.py"
        add_server_result = self.run_cli(
            ["mcp", "add-stdio", "test-mcp", "--", "uv", "run", "mcp", "run", str(server_path)],
            cwd=temp_git_repo,
        )
        assert add_server_result.returncode == 0

        # Use the existing spec2.md template that has MCP calls
        template_path = Path(__file__).parent.parent / "templates" / "spec2.md"

        # Run create-spec command with test runner and additional_context variable
        result = self.run_cli(
            [
                "create-spec",
                "--verbose",
                str(template_path),
                "--var",
                "additional_context=This is test context",
            ],
            cwd=temp_git_repo,
            use_test_runner=True,
        )

        assert result.returncode == 0

        # Verify that MCP tool was called and returned expected data
        # The template uses: call_tool('test-mcp', 'jsonTest', {'cloudId': '1234', 'ticketId': 'ACME-123'})
        # The jsonTest tool returns: {"id": "1234 - ACME-123", "summary": "Summary for ACME-123",
        # "description": "This is a mock Jira ticket description."}

        # Check that the rendered template contains the expected MCP tool output
        assert "1234 - ACME-123" in result.stdout  # ticket.id from MCP call
        assert "This is a mock Jira ticket description." in result.stdout  # ticket.description from MCP call
        assert "This is test context" in result.stdout  # additional_context variable

        # Verify template structure is preserved
        assert "# Task Template" in result.stdout
        assert "## Ticket description" in result.stdout
        assert "### Description" in result.stdout
        assert "## Additional context" in result.stdout

    def test_create_spec_with_partial_mcp_call(self, temp_git_repo):
        """Test create-spec with template that includes partial MCP tool calls requiring user input."""
        # Initialize project first
        init_result = self.run_cli(["init"], cwd=temp_git_repo)
        assert init_result.returncode == 0

        # Add test MCP server
        server_path = Path(__file__).parent.parent / "mcp_test_server.py"
        add_server_result = self.run_cli(
            ["mcp", "add-stdio", "test-mcp", "--", "uv", "run", "mcp", "run", str(server_path)],
            cwd=temp_git_repo,
        )
        assert add_server_result.returncode == 0

        # Use the existing spec3.md template that has partial MCP calls
        template_path = Path(__file__).parent.parent / "templates" / "spec3.md"

        # Run create-spec command with test runner and additional_context variable
        # The template has:
        # - call_tool('test-mcp', 'jsonTest', {'cloudId': '1234'}) - missing 'ticketId' parameter
        # - call_tool('test-mcp', 'add', {'a': 5}) - missing 'b' parameter
        result = self.run_cli(
            [
                "create-spec",
                "--verbose",
                str(template_path),
                "--var",
                "additional_context=This is test context for partial MCP",
            ],
            cwd=temp_git_repo,
            use_test_runner=True,
        )

        assert result.returncode == 0

        # Verify that MCP tools were called with both provided and collected parameters
        # For jsonTest: cloudId='1234' + ticketId from mock (should be 'mock_value_ticketId')
        # Expected output: "1234 - mock_value_ticketId"
        assert "1234 - mock_value_ticketId" in result.stdout

        # Verify the description from jsonTest call
        assert "This is a mock Jira ticket description." in result.stdout

        # For add: a=5 + b from mock (should be 10), so result should be 15
        assert "15" in result.stdout

        # Verify additional_context variable
        assert "This is test context for partial MCP" in result.stdout

        # Verify template structure is preserved
        assert "# Task Template" in result.stdout
        assert "## Ticket description" in result.stdout
        assert "### Description" in result.stdout
        assert "## Additional context" in result.stdout
        assert "## Some math..." in result.stdout

