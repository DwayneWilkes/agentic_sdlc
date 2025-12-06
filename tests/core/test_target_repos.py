"""Tests for target repository management."""

import pytest
import yaml

from src.core.target_repos import (
    TargetManager,
    TargetRepository,
    TaskIntakeConfig,
    get_target,
    get_target_manager,
)


class TestTargetRepository:
    """Tests for TargetRepository dataclass."""

    def test_basic_creation(self, tmp_path):
        """Test creating a basic target repository."""
        target = TargetRepository(
            name="Test Target",
            path=tmp_path,
            description="A test repository",
        )
        assert target.name == "Test Target"
        assert target.path == tmp_path
        assert target.description == "A test repository"

    def test_default_paths(self, tmp_path):
        """Test default paths are set correctly."""
        target = TargetRepository(name="Test", path=tmp_path)
        assert target.roadmap == "plans/roadmap.md"
        assert target.devlog == "docs/devlog.md"
        assert target.coder_agent == ".claude/agents/coder_agent.md"
        assert target.conventions == "CLAUDE.md"

    def test_path_resolution(self, tmp_path):
        """Test relative path resolution."""
        target = TargetRepository(name="Test", path="subdir")
        target.resolve(tmp_path)
        assert target.path == tmp_path / "subdir"

    def test_get_absolute_paths(self, tmp_path):
        """Test getting absolute paths to files."""
        target = TargetRepository(name="Test", path=tmp_path)
        target.resolve()

        assert target.get_roadmap_path() == tmp_path / "plans/roadmap.md"
        assert target.get_devlog_path() == tmp_path / "docs/devlog.md"
        assert target.get_conventions_path() == tmp_path / "CLAUDE.md"

    def test_identity_context_path(self, tmp_path):
        """Test identity context path resolution."""
        # Without identity context
        target1 = TargetRepository(name="Test", path=tmp_path)
        assert target1.get_identity_context_path() is None

        # With identity context
        target2 = TargetRepository(
            name="Test",
            path=tmp_path,
            identity_context="config/identity.yaml",
        )
        assert target2.get_identity_context_path() == tmp_path / "config/identity.yaml"

    def test_proposals_dir_path(self, tmp_path):
        """Test proposals directory path resolution."""
        # Without proposals dir
        target1 = TargetRepository(name="Test", path=tmp_path)
        assert target1.get_proposals_dir_path() is None

        # With proposals dir
        target2 = TargetRepository(
            name="Test",
            path=tmp_path,
            proposals_dir="proposals/pending",
        )
        assert target2.get_proposals_dir_path() == tmp_path / "proposals/pending"

    def test_exists(self, tmp_path):
        """Test existence check."""
        target = TargetRepository(name="Test", path=tmp_path)
        assert target.exists() is True

        nonexistent = TargetRepository(name="Test", path=tmp_path / "nonexistent")
        assert nonexistent.exists() is False

    def test_validate_missing_path(self, tmp_path):
        """Test validation catches missing path."""
        target = TargetRepository(name="Test", path=tmp_path / "nonexistent")
        errors = target.validate()
        assert len(errors) == 1
        assert "does not exist" in errors[0]

    def test_validate_missing_roadmap(self, tmp_path):
        """Test validation catches missing roadmap."""
        target = TargetRepository(name="Test", path=tmp_path)
        errors = target.validate()
        assert any("Roadmap not found" in e for e in errors)

    def test_validate_valid_target(self, tmp_path):
        """Test validation passes for valid target."""
        # Create required files
        (tmp_path / "plans").mkdir()
        (tmp_path / "plans" / "roadmap.md").write_text("# Roadmap")
        (tmp_path / ".claude" / "agents").mkdir(parents=True)
        (tmp_path / ".claude" / "agents" / "coder_agent.md").write_text("# Coder")

        target = TargetRepository(name="Test", path=tmp_path)
        errors = target.validate()
        assert len(errors) == 0

    def test_load_identity_context(self, tmp_path):
        """Test loading identity context content."""
        # Create identity file
        (tmp_path / "config").mkdir()
        identity_path = tmp_path / "config" / "identity.yaml"
        identity_path.write_text("anchors:\n  - curiosity\n  - creativity")

        target = TargetRepository(
            name="Test",
            path=tmp_path,
            identity_context="config/identity.yaml",
        )

        content = target.load_identity_context()
        assert content is not None
        assert "curiosity" in content

    def test_load_identity_context_missing(self, tmp_path):
        """Test loading missing identity context returns None."""
        target = TargetRepository(
            name="Test",
            path=tmp_path,
            identity_context="config/nonexistent.yaml",
        )
        assert target.load_identity_context() is None

    def test_to_dict(self, tmp_path):
        """Test serialization to dictionary."""
        target = TargetRepository(
            name="Test",
            path=tmp_path,
            description="Test description",
            identity_context="config/identity.yaml",
        )

        result = target.to_dict()
        assert result["name"] == "Test"
        assert result["path"] == str(tmp_path)
        assert result["description"] == "Test description"
        assert result["identity_context"] == "config/identity.yaml"


class TestTargetManager:
    """Tests for TargetManager class."""

    @pytest.fixture
    def config_file(self, tmp_path):
        """Create a temporary targets.yaml config."""
        config = {
            "default_target": "self",
            "targets": {
                "self": {
                    "name": "Self",
                    "path": str(tmp_path),
                    "description": "Test self target",
                },
                "external": {
                    "name": "External Project",
                    "path": str(tmp_path / "external"),
                    "description": "External test target",
                    "identity_context": "config/identity.yaml",
                    "proposals_dir": "proposals/pending",
                },
            },
            "task_intake": {
                "watch_proposals": True,
                "poll_interval_seconds": 60,
                "nats_subjects": ["test.proposals.>"],
            },
            "defaults": {
                "roadmap": "plans/roadmap.md",
            },
        }

        config_path = tmp_path / "targets.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        # Create external directory
        (tmp_path / "external").mkdir()

        return config_path

    def test_load_targets(self, config_file, tmp_path):
        """Test loading targets from config."""
        manager = TargetManager(config_file)

        targets = manager.list_targets()
        assert "self" in targets
        assert "external" in targets

    def test_get_target(self, config_file, tmp_path):
        """Test getting a specific target."""
        manager = TargetManager(config_file)

        target = manager.get_target("self")
        assert target.name == "Self"
        assert target.path == tmp_path

    def test_get_default_target(self, config_file, tmp_path):
        """Test getting default target when no ID specified."""
        manager = TargetManager(config_file)

        target = manager.get_target()  # No ID
        assert target.name == "Self"

    def test_get_nonexistent_target(self, config_file):
        """Test getting nonexistent target raises KeyError."""
        manager = TargetManager(config_file)

        with pytest.raises(KeyError) as exc_info:
            manager.get_target("nonexistent")
        assert "nonexistent" in str(exc_info.value)

    def test_external_target_config(self, config_file, tmp_path):
        """Test external target has identity context."""
        manager = TargetManager(config_file)

        target = manager.get_target("external")
        assert target.identity_context == "config/identity.yaml"
        assert target.proposals_dir == "proposals/pending"

    def test_task_intake_config(self, config_file):
        """Test task intake configuration."""
        manager = TargetManager(config_file)

        intake = manager.get_task_intake_config()
        assert intake.watch_proposals is True
        assert intake.poll_interval_seconds == 60
        assert "test.proposals.>" in intake.nats_subjects

    def test_add_target(self, config_file, tmp_path):
        """Test adding a new target."""
        manager = TargetManager(config_file)

        new_target = manager.add_target(
            target_id="new_project",
            name="New Project",
            path=tmp_path / "new_project",
            description="A new project",
        )

        assert new_target.name == "New Project"
        assert "new_project" in manager.list_targets()

    def test_defaults_applied(self, config_file, tmp_path):
        """Test that defaults are applied to targets."""
        manager = TargetManager(config_file)

        target = manager.get_target("self")
        # Default roadmap from config
        assert target.roadmap == "plans/roadmap.md"

    def test_missing_config_creates_self(self, tmp_path):
        """Test missing config creates default self target."""
        nonexistent = tmp_path / "nonexistent.yaml"
        manager = TargetManager(nonexistent)

        targets = manager.list_targets()
        assert targets == ["self"]

        target = manager.get_target("self")
        assert target.name == "Orchestrator (Self)"


class TestTaskIntakeConfig:
    """Tests for TaskIntakeConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TaskIntakeConfig()
        assert config.watch_proposals is True
        assert config.poll_interval_seconds == 30
        assert config.nats_subjects == []

    def test_custom_values(self):
        """Test custom configuration values."""
        config = TaskIntakeConfig(
            watch_proposals=False,
            poll_interval_seconds=120,
            nats_subjects=["foo.>", "bar.>"],
        )
        assert config.watch_proposals is False
        assert config.poll_interval_seconds == 120
        assert len(config.nats_subjects) == 2


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        import src.core.target_repos as tr

        tr._manager_instance = None
        yield
        tr._manager_instance = None

    def test_get_target_manager(self):
        """Test getting the singleton manager."""
        manager1 = get_target_manager()
        manager2 = get_target_manager()
        assert manager1 is manager2

    def test_get_target_function(self, tmp_path):
        """Test convenience get_target function."""
        # This will use the default config or create default self target
        import src.core.target_repos as tr

        tr._manager_instance = None

        # Create a test config
        config = {
            "default_target": "test",
            "targets": {
                "test": {
                    "name": "Test",
                    "path": str(tmp_path),
                },
            },
        }

        config_path = tmp_path / "targets.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        manager = TargetManager(config_path)
        tr._manager_instance = manager

        target = get_target("test")
        assert target.name == "Test"
