"""Agent sandboxing and isolation.

This module provides sandboxing capabilities to restrict what agents can access
and execute, ensuring they operate within defined boundaries.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class SandboxViolationType(Enum):
    """Types of sandbox violations."""

    FILE_ACCESS = "file_access"
    COMMAND_EXECUTION = "command_execution"
    MEMORY_LIMIT = "memory_limit"
    FILE_SIZE_LIMIT = "file_size_limit"
    NETWORK_ACCESS = "network_access"
    SUBPROCESS_DENIED = "subprocess_denied"


class SandboxViolation(Exception):
    """Exception raised when agent violates sandbox policy."""

    def __init__(
        self,
        violation_type: SandboxViolationType,
        message: str,
        attempted_action: str = "",
    ):
        """Initialize sandbox violation.

        Args:
            violation_type: Type of violation that occurred
            message: Human-readable description of the violation
            attempted_action: What the agent tried to do
        """
        self.violation_type = violation_type
        self.message = message
        self.attempted_action = attempted_action
        super().__init__(message)


@dataclass
class SandboxConfig:
    """Configuration for agent sandbox."""

    allowed_paths: list[str] = field(default_factory=list)
    """Paths the agent is allowed to access."""

    allowed_commands: list[str] = field(default_factory=list)
    """Commands the agent is allowed to execute."""

    max_file_size_mb: float = 10
    """Maximum file size in MB the agent can create/read."""

    max_memory_mb: int = 512
    """Maximum memory usage in MB."""

    enable_network: bool = False
    """Whether to allow network access."""

    enable_subprocess: bool = False
    """Whether to allow subprocess execution."""


@dataclass
class AgentSandbox:
    """Sandbox for restricting agent actions.

    The sandbox enforces security policies to prevent agents from:
    - Accessing files outside allowed paths
    - Executing unauthorized commands
    - Exceeding resource limits
    - Interfering with other agents
    """

    agent_id: str
    """Unique identifier for the agent."""

    config: SandboxConfig
    """Sandbox configuration."""

    _violations: list[SandboxViolation] = field(default_factory=list, init=False)
    """History of violations (for tracking)."""

    def validate_file_access(self, file_path: str) -> None:
        """Validate that agent can access the specified file.

        Args:
            file_path: Path to the file

        Raises:
            SandboxViolation: If file access is not allowed
        """
        # Resolve to absolute path to prevent path traversal
        try:
            abs_path = Path(file_path).resolve()
        except (OSError, RuntimeError) as e:
            violation = SandboxViolation(
                violation_type=SandboxViolationType.FILE_ACCESS,
                message=f"Invalid file path: {file_path}",
                attempted_action=file_path,
            )
            self._violations.append(violation)
            raise violation from e

        # Check if symlink points outside allowed directories
        if abs_path.is_symlink():
            real_path = abs_path.resolve()
            if not self._is_path_allowed(str(real_path)):
                violation = SandboxViolation(
                    violation_type=SandboxViolationType.FILE_ACCESS,
                    message=f"Symlink points to forbidden path: {real_path}",
                    attempted_action=file_path,
                )
                self._violations.append(violation)
                raise violation

        # Check if path is in allowed directories
        if not self._is_path_allowed(str(abs_path)):
            violation = SandboxViolation(
                violation_type=SandboxViolationType.FILE_ACCESS,
                message=f"Access denied to path: {abs_path}. Not in allowed paths.",
                attempted_action=file_path,
            )
            self._violations.append(violation)
            raise violation

    def validate_command(self, command: str) -> None:
        """Validate that agent can execute the specified command.

        Args:
            command: Command to execute

        Raises:
            SandboxViolation: If command execution is not allowed
        """
        # Check if subprocess execution is enabled
        if not self.config.enable_subprocess:
            violation = SandboxViolation(
                violation_type=SandboxViolationType.SUBPROCESS_DENIED,
                message="Subprocess execution is disabled for this agent",
                attempted_action=command,
            )
            self._violations.append(violation)
            raise violation

        # Extract base command (first word)
        base_command = command.split()[0] if command else ""

        # Check if command is in allowed list
        if base_command not in self.config.allowed_commands:
            violation = SandboxViolation(
                violation_type=SandboxViolationType.COMMAND_EXECUTION,
                message=f"Command '{base_command}' not in allowed commands list",
                attempted_action=command,
            )
            self._violations.append(violation)
            raise violation

    def validate_file_size(self, size_mb: float) -> None:
        """Validate that file size is within limits.

        Args:
            size_mb: File size in MB

        Raises:
            SandboxViolation: If file size exceeds limit
        """
        if size_mb > self.config.max_file_size_mb:
            violation = SandboxViolation(
                violation_type=SandboxViolationType.FILE_SIZE_LIMIT,
                message=f"File size {size_mb}MB exceeds limit of {self.config.max_file_size_mb}MB",
                attempted_action=f"{size_mb}MB",
            )
            self._violations.append(violation)
            raise violation

    def validate_memory_usage(self, memory_mb: int) -> None:
        """Validate that memory usage is within limits.

        Args:
            memory_mb: Memory usage in MB

        Raises:
            SandboxViolation: If memory usage exceeds limit
        """
        if memory_mb > self.config.max_memory_mb:
            violation = SandboxViolation(
                violation_type=SandboxViolationType.MEMORY_LIMIT,
                message=(
                    f"Memory usage {memory_mb}MB exceeds "
                    f"limit of {self.config.max_memory_mb}MB"
                ),
                attempted_action=f"{memory_mb}MB",
            )
            self._violations.append(violation)
            raise violation

    def validate_network_access(self, url: str) -> None:
        """Validate that network access is allowed.

        Args:
            url: URL to access

        Raises:
            SandboxViolation: If network access is not allowed
        """
        if not self.config.enable_network:
            violation = SandboxViolation(
                violation_type=SandboxViolationType.NETWORK_ACCESS,
                message="Network access is disabled for this agent",
                attempted_action=url,
            )
            self._violations.append(violation)
            raise violation

    def get_violations(self) -> list[SandboxViolation]:
        """Get history of sandbox violations.

        Returns:
            List of all violations that occurred
        """
        return self._violations.copy()

    def _is_path_allowed(self, path: str) -> bool:
        """Check if path is within allowed directories.

        Args:
            path: Absolute path to check

        Returns:
            True if path is allowed, False otherwise
        """
        if not self.config.allowed_paths:
            return False

        abs_path = Path(path).resolve()

        for allowed_path in self.config.allowed_paths:
            try:
                allowed_abs = Path(allowed_path).resolve()
                # Check if path is under allowed directory
                if abs_path == allowed_abs or allowed_abs in abs_path.parents:
                    return True
            except (OSError, RuntimeError):
                continue

        return False
