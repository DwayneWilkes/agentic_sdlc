"""Tests for agent sandboxing and isolation."""

import os
import tempfile
from pathlib import Path

import pytest

from src.security.sandbox import (
    AgentSandbox,
    SandboxConfig,
    SandboxViolation,
    SandboxViolationType,
)


class TestSandboxConfig:
    """Test SandboxConfig dataclass."""

    def test_default_config(self):
        """Test default sandbox configuration."""
        config = SandboxConfig()
        assert config.allowed_paths == []
        assert config.allowed_commands == []
        assert config.max_file_size_mb == 10
        assert config.max_memory_mb == 512
        assert config.enable_network is False
        assert config.enable_subprocess is False

    def test_custom_config(self):
        """Test custom sandbox configuration."""
        config = SandboxConfig(
            allowed_paths=["/tmp/workspace"],
            allowed_commands=["git", "pytest"],
            max_file_size_mb=50,
            max_memory_mb=1024,
            enable_network=True,
            enable_subprocess=True,
        )
        assert "/tmp/workspace" in config.allowed_paths
        assert "git" in config.allowed_commands
        assert config.max_file_size_mb == 50
        assert config.max_memory_mb == 1024
        assert config.enable_network is True
        assert config.enable_subprocess is True


class TestSandboxViolation:
    """Test SandboxViolation exception."""

    def test_violation_creation(self):
        """Test creating a sandbox violation."""
        violation = SandboxViolation(
            violation_type=SandboxViolationType.FILE_ACCESS,
            message="Attempted to access forbidden path",
            attempted_action="/etc/passwd",
        )
        assert violation.violation_type == SandboxViolationType.FILE_ACCESS
        assert "forbidden path" in violation.message
        assert violation.attempted_action == "/etc/passwd"

    def test_violation_types(self):
        """Test all violation types exist."""
        assert SandboxViolationType.FILE_ACCESS
        assert SandboxViolationType.COMMAND_EXECUTION
        assert SandboxViolationType.MEMORY_LIMIT
        assert SandboxViolationType.FILE_SIZE_LIMIT
        assert SandboxViolationType.NETWORK_ACCESS
        assert SandboxViolationType.SUBPROCESS_DENIED


class TestAgentSandbox:
    """Test AgentSandbox class."""

    def test_sandbox_creation(self):
        """Test creating a sandbox."""
        config = SandboxConfig(allowed_paths=["/tmp"])
        sandbox = AgentSandbox(agent_id="test-agent", config=config)
        assert sandbox.agent_id == "test-agent"
        assert sandbox.config == config

    def test_validate_file_access_allowed(self):
        """Test validating allowed file access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SandboxConfig(allowed_paths=[tmpdir])
            sandbox = AgentSandbox(agent_id="test-agent", config=config)

            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")

            # Should not raise exception
            sandbox.validate_file_access(str(test_file))

    def test_validate_file_access_denied(self):
        """Test blocking forbidden file access."""
        config = SandboxConfig(allowed_paths=["/tmp/allowed"])
        sandbox = AgentSandbox(agent_id="test-agent", config=config)

        with pytest.raises(SandboxViolation) as exc_info:
            sandbox.validate_file_access("/etc/passwd")

        assert exc_info.value.violation_type == SandboxViolationType.FILE_ACCESS
        assert "/etc/passwd" in exc_info.value.attempted_action

    def test_validate_file_access_relative_path(self):
        """Test handling relative paths correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SandboxConfig(allowed_paths=[tmpdir])
            sandbox = AgentSandbox(agent_id="test-agent", config=config)

            # Should resolve relative paths and check them
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                # Relative path within allowed directory
                sandbox.validate_file_access("./test.txt")
            finally:
                os.chdir(original_cwd)

    def test_validate_command_allowed(self):
        """Test validating allowed commands."""
        config = SandboxConfig(
            allowed_commands=["git", "pytest"],
            enable_subprocess=True,
        )
        sandbox = AgentSandbox(agent_id="test-agent", config=config)

        # Should not raise exception
        sandbox.validate_command("git status")
        sandbox.validate_command("pytest tests/")

    def test_validate_command_denied(self):
        """Test blocking forbidden commands."""
        config = SandboxConfig(
            allowed_commands=["git"],
            enable_subprocess=True,
        )
        sandbox = AgentSandbox(agent_id="test-agent", config=config)

        with pytest.raises(SandboxViolation) as exc_info:
            sandbox.validate_command("rm -rf /")

        assert exc_info.value.violation_type == SandboxViolationType.COMMAND_EXECUTION

    def test_validate_command_subprocess_disabled(self):
        """Test blocking all commands when subprocess is disabled."""
        config = SandboxConfig(
            allowed_commands=["git"],
            enable_subprocess=False,
        )
        sandbox = AgentSandbox(agent_id="test-agent", config=config)

        with pytest.raises(SandboxViolation) as exc_info:
            sandbox.validate_command("git status")

        assert exc_info.value.violation_type == SandboxViolationType.SUBPROCESS_DENIED

    def test_validate_file_size_allowed(self):
        """Test validating allowed file size."""
        config = SandboxConfig(max_file_size_mb=1)
        sandbox = AgentSandbox(agent_id="test-agent", config=config)

        # 0.5 MB should be allowed
        sandbox.validate_file_size(0.5)

    def test_validate_file_size_denied(self):
        """Test blocking oversized files."""
        config = SandboxConfig(max_file_size_mb=1)
        sandbox = AgentSandbox(agent_id="test-agent", config=config)

        with pytest.raises(SandboxViolation) as exc_info:
            sandbox.validate_file_size(2.0)

        assert exc_info.value.violation_type == SandboxViolationType.FILE_SIZE_LIMIT

    def test_validate_memory_usage_allowed(self):
        """Test validating allowed memory usage."""
        config = SandboxConfig(max_memory_mb=512)
        sandbox = AgentSandbox(agent_id="test-agent", config=config)

        # 256 MB should be allowed
        sandbox.validate_memory_usage(256)

    def test_validate_memory_usage_denied(self):
        """Test blocking excessive memory usage."""
        config = SandboxConfig(max_memory_mb=512)
        sandbox = AgentSandbox(agent_id="test-agent", config=config)

        with pytest.raises(SandboxViolation) as exc_info:
            sandbox.validate_memory_usage(1024)

        assert exc_info.value.violation_type == SandboxViolationType.MEMORY_LIMIT

    def test_validate_network_access_allowed(self):
        """Test allowing network access when enabled."""
        config = SandboxConfig(enable_network=True)
        sandbox = AgentSandbox(agent_id="test-agent", config=config)

        # Should not raise exception
        sandbox.validate_network_access("https://api.example.com")

    def test_validate_network_access_denied(self):
        """Test blocking network access when disabled."""
        config = SandboxConfig(enable_network=False)
        sandbox = AgentSandbox(agent_id="test-agent", config=config)

        with pytest.raises(SandboxViolation) as exc_info:
            sandbox.validate_network_access("https://api.example.com")

        assert exc_info.value.violation_type == SandboxViolationType.NETWORK_ACCESS

    def test_get_violations_empty(self):
        """Test getting violations when none occurred."""
        config = SandboxConfig()
        sandbox = AgentSandbox(agent_id="test-agent", config=config)

        violations = sandbox.get_violations()
        assert violations == []

    def test_get_violations_tracking(self):
        """Test that violations are tracked."""
        config = SandboxConfig(allowed_paths=["/tmp"])
        sandbox = AgentSandbox(agent_id="test-agent", config=config)

        # Trigger violations (catch them so test continues)
        try:
            sandbox.validate_file_access("/etc/passwd")
        except SandboxViolation:
            pass

        try:
            sandbox.validate_file_access("/var/log/syslog")
        except SandboxViolation:
            pass

        violations = sandbox.get_violations()
        assert len(violations) == 2
        assert all(v.violation_type == SandboxViolationType.FILE_ACCESS for v in violations)

    def test_isolation_between_sandboxes(self):
        """Test that different agent sandboxes are isolated."""
        config1 = SandboxConfig(allowed_paths=["/tmp/agent1"])
        config2 = SandboxConfig(allowed_paths=["/tmp/agent2"])

        sandbox1 = AgentSandbox(agent_id="agent-1", config=config1)
        sandbox2 = AgentSandbox(agent_id="agent-2", config=config2)

        # Trigger violation in sandbox1
        try:
            sandbox1.validate_file_access("/etc/passwd")
        except SandboxViolation:
            pass

        # sandbox2 should have no violations
        assert len(sandbox1.get_violations()) == 1
        assert len(sandbox2.get_violations()) == 0

    def test_path_traversal_attack_prevention(self):
        """Test preventing path traversal attacks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SandboxConfig(allowed_paths=[tmpdir])
            sandbox = AgentSandbox(agent_id="test-agent", config=config)

            # Try to escape using path traversal
            with pytest.raises(SandboxViolation):
                sandbox.validate_file_access(f"{tmpdir}/../../../etc/passwd")

    def test_symlink_escape_prevention(self):
        """Test preventing escape via symlinks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SandboxConfig(allowed_paths=[tmpdir])
            sandbox = AgentSandbox(agent_id="test-agent", config=config)

            # Create a symlink pointing outside allowed directory
            link_path = Path(tmpdir) / "escape_link"
            link_path.symlink_to("/etc/passwd")

            # Should detect and block access to symlink target
            with pytest.raises(SandboxViolation):
                sandbox.validate_file_access(str(link_path))
