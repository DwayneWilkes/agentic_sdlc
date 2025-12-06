"""
Target Repository Management - Enables orchestrator to work on external codebases.

This module loads target repository configurations and provides context
for agents working on repositories other than the orchestrator itself.
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class TargetRepository:
    """Configuration for a target repository that agents can work on."""

    name: str
    path: Path
    description: str = ""

    # Standard paths relative to target root
    roadmap: str = "plans/roadmap.md"
    devlog: str = "docs/devlog.md"
    coder_agent: str = ".claude/agents/coder_agent.md"
    pm_agent: str = ".claude/agents/project_manager.md"
    conventions: str = "CLAUDE.md"

    # Optional paths
    identity_context: str | None = None
    proposals_dir: str | None = None

    # Resolved absolute paths (set after initialization)
    _resolved: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        """Convert path to Path object if string."""
        if isinstance(self.path, str):
            self.path = Path(self.path)

    def resolve(self, base_path: Path | None = None) -> "TargetRepository":
        """
        Resolve relative paths to absolute paths.

        Args:
            base_path: Base path for resolving relative target paths.
                      If None, uses current working directory.

        Returns:
            Self with resolved paths
        """
        if self._resolved:
            return self

        if base_path is None:
            base_path = Path.cwd()

        # Resolve the target path itself
        if not self.path.is_absolute():
            self.path = (base_path / self.path).resolve()

        self._resolved = True
        return self

    def get_roadmap_path(self) -> Path:
        """Get absolute path to roadmap."""
        return self.path / self.roadmap

    def get_devlog_path(self) -> Path:
        """Get absolute path to devlog."""
        return self.path / self.devlog

    def get_coder_agent_path(self) -> Path:
        """Get absolute path to coder agent workflow."""
        return self.path / self.coder_agent

    def get_pm_agent_path(self) -> Path:
        """Get absolute path to PM agent workflow."""
        return self.path / self.pm_agent

    def get_conventions_path(self) -> Path:
        """Get absolute path to conventions file (CLAUDE.md)."""
        return self.path / self.conventions

    def get_identity_context_path(self) -> Path | None:
        """Get absolute path to identity context file, if configured."""
        if self.identity_context:
            return self.path / self.identity_context
        return None

    def get_proposals_dir_path(self) -> Path | None:
        """Get absolute path to proposals directory, if configured."""
        if self.proposals_dir:
            return self.path / self.proposals_dir
        return None

    def exists(self) -> bool:
        """Check if the target repository path exists."""
        return self.path.exists() and self.path.is_dir()

    def validate(self) -> list[str]:
        """
        Validate the target repository configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.exists():
            errors.append(f"Target path does not exist: {self.path}")
            return errors  # Can't validate further

        # Check required files
        if not self.get_roadmap_path().exists():
            errors.append(f"Roadmap not found: {self.get_roadmap_path()}")

        if not self.get_coder_agent_path().exists():
            errors.append(f"Coder agent workflow not found: {self.get_coder_agent_path()}")

        # Optional files - warn but don't error
        if self.identity_context and not self.get_identity_context_path().exists():
            errors.append(f"Identity context not found: {self.get_identity_context_path()}")

        return errors

    def load_identity_context(self) -> str | None:
        """
        Load identity context content if configured.

        Returns:
            Identity context content as string, or None if not configured
        """
        path = self.get_identity_context_path()
        if path and path.exists():
            return path.read_text()
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "path": str(self.path),
            "description": self.description,
            "roadmap": self.roadmap,
            "devlog": self.devlog,
            "coder_agent": self.coder_agent,
            "pm_agent": self.pm_agent,
            "conventions": self.conventions,
            "identity_context": self.identity_context,
            "proposals_dir": self.proposals_dir,
        }


@dataclass
class TaskIntakeConfig:
    """Configuration for receiving tasks from external sources."""

    watch_proposals: bool = True
    poll_interval_seconds: int = 30
    nats_subjects: list[str] = field(default_factory=list)


class TargetManager:
    """Manages target repository configurations."""

    def __init__(self, config_path: Path | None = None):
        """
        Initialize the target manager.

        Args:
            config_path: Path to targets.yaml config file.
                        Defaults to config/targets.yaml
        """
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "targets.yaml"

        self.config_path = config_path
        self.project_root = config_path.parent.parent
        self._targets: dict[str, TargetRepository] = {}
        self._default_target: str = "self"
        self._defaults: dict = {}
        self._task_intake: TaskIntakeConfig = TaskIntakeConfig()
        self._loaded = False

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if self._loaded:
            return

        if not self.config_path.exists():
            # Create default configuration with just "self" target
            self._targets["self"] = TargetRepository(
                name="Orchestrator (Self)",
                path=self.project_root,
                description="The orchestrator's own codebase",
            ).resolve(self.project_root)
            self._loaded = True
            return

        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        # Load defaults
        self._defaults = config.get("defaults", {})
        self._default_target = config.get("default_target", "self")

        # Load task intake config
        intake_config = config.get("task_intake", {})
        self._task_intake = TaskIntakeConfig(
            watch_proposals=intake_config.get("watch_proposals", True),
            poll_interval_seconds=intake_config.get("poll_interval_seconds", 30),
            nats_subjects=intake_config.get("nats_subjects", []),
        )

        # Load targets
        targets_config = config.get("targets", {})
        for target_id, target_config in targets_config.items():
            # Merge with defaults
            merged = {**self._defaults, **target_config}

            target = TargetRepository(
                name=merged.get("name", target_id),
                path=merged.get("path", "."),
                description=merged.get("description", ""),
                roadmap=merged.get("roadmap", "plans/roadmap.md"),
                devlog=merged.get("devlog", "docs/devlog.md"),
                coder_agent=merged.get("coder_agent", ".claude/agents/coder_agent.md"),
                pm_agent=merged.get("pm_agent", ".claude/agents/project_manager.md"),
                conventions=merged.get("conventions", "CLAUDE.md"),
                identity_context=merged.get("identity_context"),
                proposals_dir=merged.get("proposals_dir"),
            )
            target.resolve(self.project_root)
            self._targets[target_id] = target

        self._loaded = True

    def get_target(self, target_id: str | None = None) -> TargetRepository:
        """
        Get a target repository by ID.

        Args:
            target_id: Target ID. If None, returns the default target.

        Returns:
            TargetRepository configuration

        Raises:
            KeyError: If target_id not found
        """
        self._load_config()

        if target_id is None:
            target_id = self._default_target

        if target_id not in self._targets:
            available = list(self._targets.keys())
            raise KeyError(f"Target '{target_id}' not found. Available: {available}")

        return self._targets[target_id]

    def list_targets(self) -> list[str]:
        """Get list of available target IDs."""
        self._load_config()
        return list(self._targets.keys())

    def get_all_targets(self) -> dict[str, TargetRepository]:
        """Get all target configurations."""
        self._load_config()
        return self._targets.copy()

    def get_default_target_id(self) -> str:
        """Get the default target ID."""
        self._load_config()
        return self._default_target

    def get_task_intake_config(self) -> TaskIntakeConfig:
        """Get task intake configuration."""
        self._load_config()
        return self._task_intake

    def add_target(
        self,
        target_id: str,
        name: str,
        path: str | Path,
        **kwargs,
    ) -> TargetRepository:
        """
        Add a new target repository.

        Args:
            target_id: Unique identifier for the target
            name: Human-readable name
            path: Path to the repository
            **kwargs: Additional TargetRepository fields

        Returns:
            The created TargetRepository
        """
        self._load_config()

        # Merge with defaults
        merged = {**self._defaults, **kwargs}

        target = TargetRepository(
            name=name,
            path=Path(path),
            description=merged.get("description", ""),
            roadmap=merged.get("roadmap", "plans/roadmap.md"),
            devlog=merged.get("devlog", "docs/devlog.md"),
            coder_agent=merged.get("coder_agent", ".claude/agents/coder_agent.md"),
            pm_agent=merged.get("pm_agent", ".claude/agents/project_manager.md"),
            conventions=merged.get("conventions", "CLAUDE.md"),
            identity_context=merged.get("identity_context"),
            proposals_dir=merged.get("proposals_dir"),
        )
        target.resolve(self.project_root)

        self._targets[target_id] = target
        return target

    def save_config(self) -> None:
        """Save current configuration back to YAML file."""
        config = {
            "default_target": self._default_target,
            "targets": {},
            "task_intake": {
                "watch_proposals": self._task_intake.watch_proposals,
                "poll_interval_seconds": self._task_intake.poll_interval_seconds,
                "nats_subjects": self._task_intake.nats_subjects,
            },
            "defaults": self._defaults,
        }

        for target_id, target in self._targets.items():
            config["targets"][target_id] = target.to_dict()

        with open(self.config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)


# Singleton instance
_manager_instance: TargetManager | None = None


def get_target_manager() -> TargetManager:
    """Get the global target manager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = TargetManager()
    return _manager_instance


def get_target(target_id: str | None = None) -> TargetRepository:
    """
    Convenience function to get a target repository.

    Args:
        target_id: Target ID. If None, returns the default target.

    Returns:
        TargetRepository configuration
    """
    return get_target_manager().get_target(target_id)


def add_target(
    target_id: str,
    name: str,
    path: str | Path,
    **kwargs,
) -> TargetRepository:
    """
    Convenience function to add a new target repository.

    Args:
        target_id: Unique identifier for the target
        name: Human-readable name
        path: Path to the repository
        **kwargs: Additional TargetRepository fields

    Returns:
        The created TargetRepository
    """
    return get_target_manager().add_target(target_id, name, path, **kwargs)
