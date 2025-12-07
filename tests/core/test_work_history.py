"""Tests for the WorkHistory module."""

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.core.work_history import (
    WorkHistory,
    get_work_history,
    record_phase_completion,
    get_agent_completed_phases,
)


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def temp_history_file(temp_config_dir):
    """Create a temporary work history file."""
    return temp_config_dir / "work_history.json"


@pytest.fixture
def sample_history_data():
    """Sample work history data."""
    return {
        "agents": {
            "Aria": {
                "projects": {
                    "agentic_sdlc": {
                        "completed": [
                            {"phase_id": "1.1", "completed_at": "2025-12-01T10:00:00"},
                            {"phase_id": "1.2", "completed_at": "2025-12-02T10:00:00"},
                        ]
                    },
                    "other_project": {
                        "completed": [
                            {"phase_id": "2.1", "completed_at": "2025-12-03T10:00:00"},
                        ]
                    }
                }
            },
            "Cipher": {
                "projects": {
                    "agentic_sdlc": {
                        "completed": [
                            {"phase_id": "2.1", "completed_at": "2025-12-04T10:00:00"},
                        ]
                    }
                }
            }
        },
        "last_updated": "2025-12-04T10:00:00"
    }


class TestWorkHistoryInit:
    """Tests for WorkHistory initialization."""

    def test_init_with_default_path(self):
        """Test initialization with default path."""
        history = WorkHistory()
        assert history.config_path.name == "work_history.json"

    def test_init_with_custom_path(self, temp_history_file):
        """Test initialization with custom path."""
        history = WorkHistory(config_path=temp_history_file)
        assert history.config_path == temp_history_file
        assert history.project_id == temp_history_file.parent.parent.name

    def test_init_with_custom_project_id(self, temp_history_file):
        """Test initialization with custom project ID."""
        history = WorkHistory(config_path=temp_history_file, project_id="my_project")
        assert history.project_id == "my_project"

    def test_init_creates_empty_data_when_no_file(self, temp_history_file):
        """Test initialization creates empty data when file doesn't exist."""
        history = WorkHistory(config_path=temp_history_file)
        assert history.data == {"agents": {}, "last_updated": None}

    def test_init_loads_existing_data(self, temp_history_file, sample_history_data):
        """Test initialization loads existing data from file."""
        temp_history_file.write_text(json.dumps(sample_history_data))
        history = WorkHistory(config_path=temp_history_file)
        assert history.data == sample_history_data


class TestLoadData:
    """Tests for _load_data method."""

    def test_load_data_from_existing_file(self, temp_history_file, sample_history_data):
        """Test loading data from existing file."""
        temp_history_file.write_text(json.dumps(sample_history_data))
        history = WorkHistory(config_path=temp_history_file)
        assert history.data["agents"]["Aria"]["projects"]["agentic_sdlc"]["completed"][0]["phase_id"] == "1.1"

    def test_load_data_from_nonexistent_file(self, temp_history_file):
        """Test loading returns empty data when file doesn't exist."""
        history = WorkHistory(config_path=temp_history_file)
        assert history.data["agents"] == {}


class TestSaveData:
    """Tests for _save_data method."""

    def test_save_data_creates_file(self, temp_history_file):
        """Test that save creates the file."""
        history = WorkHistory(config_path=temp_history_file, project_id="test")
        history.data["agents"]["Test"] = {"projects": {}}
        history._save_data()

        assert temp_history_file.exists()
        saved_data = json.loads(temp_history_file.read_text())
        assert "Test" in saved_data["agents"]
        assert saved_data["last_updated"] is not None

    def test_save_data_updates_timestamp(self, temp_history_file):
        """Test that save updates the timestamp."""
        history = WorkHistory(config_path=temp_history_file, project_id="test")
        history._save_data()

        saved_data = json.loads(temp_history_file.read_text())
        # Timestamp should be a valid ISO format
        timestamp = datetime.fromisoformat(saved_data["last_updated"])
        assert timestamp is not None


class TestRecordCompletion:
    """Tests for record_completion method."""

    def test_record_completion_new_agent(self, temp_history_file):
        """Test recording completion for new agent."""
        history = WorkHistory(config_path=temp_history_file, project_id="test_project")
        result = history.record_completion("NewAgent", "1.1")

        assert result is True
        assert "NewAgent" in history.data["agents"]
        completed = history.data["agents"]["NewAgent"]["projects"]["test_project"]["completed"]
        assert len(completed) == 1
        assert completed[0]["phase_id"] == "1.1"

    def test_record_completion_existing_agent(self, temp_history_file, sample_history_data):
        """Test recording completion for existing agent."""
        temp_history_file.write_text(json.dumps(sample_history_data))
        history = WorkHistory(config_path=temp_history_file, project_id="agentic_sdlc")
        result = history.record_completion("Aria", "1.3")

        assert result is True
        completed = history.data["agents"]["Aria"]["projects"]["agentic_sdlc"]["completed"]
        assert len(completed) == 3
        assert completed[-1]["phase_id"] == "1.3"

    def test_record_completion_custom_project(self, temp_history_file):
        """Test recording completion with custom project ID."""
        history = WorkHistory(config_path=temp_history_file, project_id="default")
        result = history.record_completion("Agent", "1.1", project_id="custom_project")

        assert result is True
        assert "custom_project" in history.data["agents"]["Agent"]["projects"]

    def test_record_completion_with_details(self, temp_history_file):
        """Test recording completion with additional details."""
        history = WorkHistory(config_path=temp_history_file, project_id="test")
        details = {"duration_minutes": 30, "commit_hash": "abc123"}
        result = history.record_completion("Agent", "1.1", details=details)

        assert result is True
        completed = history.data["agents"]["Agent"]["projects"]["test"]["completed"][0]
        assert completed["duration_minutes"] == 30
        assert completed["commit_hash"] == "abc123"

    def test_record_completion_idempotent(self, temp_history_file):
        """Test recording same completion twice is idempotent."""
        history = WorkHistory(config_path=temp_history_file, project_id="test")
        history.record_completion("Agent", "1.1")
        result = history.record_completion("Agent", "1.1")

        assert result is True
        completed = history.data["agents"]["Agent"]["projects"]["test"]["completed"]
        assert len(completed) == 1  # Only one entry, not two


class TestGetCompletedPhases:
    """Tests for get_completed_phases method."""

    def test_get_completed_phases_existing_agent(self, temp_history_file, sample_history_data):
        """Test getting phases for existing agent."""
        temp_history_file.write_text(json.dumps(sample_history_data))
        history = WorkHistory(config_path=temp_history_file, project_id="agentic_sdlc")

        phases = history.get_completed_phases("Aria")
        assert phases == ["1.1", "1.2"]

    def test_get_completed_phases_nonexistent_agent(self, temp_history_file):
        """Test getting phases for nonexistent agent."""
        history = WorkHistory(config_path=temp_history_file, project_id="test")

        phases = history.get_completed_phases("Ghost")
        assert phases == []

    def test_get_completed_phases_custom_project(self, temp_history_file, sample_history_data):
        """Test getting phases for different project."""
        temp_history_file.write_text(json.dumps(sample_history_data))
        history = WorkHistory(config_path=temp_history_file, project_id="default")

        phases = history.get_completed_phases("Aria", project_id="other_project")
        assert phases == ["2.1"]


class TestGetCompletionDetails:
    """Tests for get_completion_details method."""

    def test_get_completion_details_existing(self, temp_history_file, sample_history_data):
        """Test getting details for existing completion."""
        temp_history_file.write_text(json.dumps(sample_history_data))
        history = WorkHistory(config_path=temp_history_file, project_id="agentic_sdlc")

        details = history.get_completion_details("Aria", "1.1")
        assert details is not None
        assert details["phase_id"] == "1.1"
        assert details["completed_at"] == "2025-12-01T10:00:00"

    def test_get_completion_details_nonexistent_phase(self, temp_history_file, sample_history_data):
        """Test getting details for nonexistent phase."""
        temp_history_file.write_text(json.dumps(sample_history_data))
        history = WorkHistory(config_path=temp_history_file, project_id="agentic_sdlc")

        details = history.get_completion_details("Aria", "9.9")
        assert details is None

    def test_get_completion_details_nonexistent_agent(self, temp_history_file):
        """Test getting details for nonexistent agent."""
        history = WorkHistory(config_path=temp_history_file, project_id="test")

        details = history.get_completion_details("Ghost", "1.1")
        assert details is None


class TestGetAgentExperience:
    """Tests for get_agent_experience method."""

    def test_get_agent_experience(self, temp_history_file, sample_history_data):
        """Test getting all agents' experience for a project."""
        temp_history_file.write_text(json.dumps(sample_history_data))
        history = WorkHistory(config_path=temp_history_file, project_id="agentic_sdlc")

        experience = history.get_agent_experience()
        assert "Aria" in experience
        assert "Cipher" in experience
        assert experience["Aria"] == ["1.1", "1.2"]
        assert experience["Cipher"] == ["2.1"]

    def test_get_agent_experience_custom_project(self, temp_history_file, sample_history_data):
        """Test getting experience for different project."""
        temp_history_file.write_text(json.dumps(sample_history_data))
        history = WorkHistory(config_path=temp_history_file, project_id="default")

        experience = history.get_agent_experience(project_id="other_project")
        assert experience["Aria"] == ["2.1"]
        assert experience["Cipher"] == []  # No completions in other_project


class TestGetAllExperience:
    """Tests for get_all_experience method."""

    def test_get_all_experience(self, temp_history_file, sample_history_data):
        """Test getting all experience across all projects."""
        temp_history_file.write_text(json.dumps(sample_history_data))
        history = WorkHistory(config_path=temp_history_file, project_id="test")

        all_exp = history.get_all_experience()
        assert "Aria" in all_exp
        assert "Cipher" in all_exp
        assert "agentic_sdlc" in all_exp["Aria"]
        assert "other_project" in all_exp["Aria"]
        assert all_exp["Aria"]["agentic_sdlc"] == ["1.1", "1.2"]

    def test_get_all_experience_empty(self, temp_history_file):
        """Test getting all experience when empty."""
        history = WorkHistory(config_path=temp_history_file, project_id="test")

        all_exp = history.get_all_experience()
        assert all_exp == {}


class TestMigrateFromAgentNames:
    """Tests for migrate_from_agent_names method."""

    def test_migrate_list_format(self, temp_history_file, tmp_path):
        """Test migrating from legacy list format."""
        agent_names_path = tmp_path / "agent_names.json"
        legacy_data = {
            "assigned_names": {
                "agent-001": {
                    "name": "OldAgent",
                    "completed_phases": ["1.1", "1.2"]
                }
            }
        }
        agent_names_path.write_text(json.dumps(legacy_data))

        history = WorkHistory(config_path=temp_history_file, project_id="test")
        migrated = history.migrate_from_agent_names(agent_names_path)

        assert migrated == 2
        phases = history.get_completed_phases("OldAgent")
        assert "1.1" in phases
        assert "1.2" in phases

    def test_migrate_dict_format(self, temp_history_file, tmp_path):
        """Test migrating from dict format."""
        agent_names_path = tmp_path / "agent_names.json"
        legacy_data = {
            "assigned_names": {
                "agent-001": {
                    "name": "OldAgent",
                    "completed_phases": {
                        "project_a": ["1.1"],
                        "project_b": ["2.1", "2.2"]
                    }
                }
            }
        }
        agent_names_path.write_text(json.dumps(legacy_data))

        history = WorkHistory(config_path=temp_history_file, project_id="test")
        migrated = history.migrate_from_agent_names(agent_names_path)

        assert migrated == 3
        phases_a = history.get_completed_phases("OldAgent", project_id="project_a")
        assert phases_a == ["1.1"]
        phases_b = history.get_completed_phases("OldAgent", project_id="project_b")
        assert "2.1" in phases_b
        assert "2.2" in phases_b

    def test_migrate_nonexistent_file(self, temp_history_file, tmp_path):
        """Test migrating from nonexistent file."""
        agent_names_path = tmp_path / "nonexistent.json"

        history = WorkHistory(config_path=temp_history_file, project_id="test")
        migrated = history.migrate_from_agent_names(agent_names_path)

        assert migrated == 0

    def test_migrate_no_name(self, temp_history_file, tmp_path):
        """Test migrating skips entries without personal name."""
        agent_names_path = tmp_path / "agent_names.json"
        legacy_data = {
            "assigned_names": {
                "agent-001": {
                    "completed_phases": ["1.1"]
                    # No "name" field
                }
            }
        }
        agent_names_path.write_text(json.dumps(legacy_data))

        history = WorkHistory(config_path=temp_history_file, project_id="test")
        migrated = history.migrate_from_agent_names(agent_names_path)

        assert migrated == 0


class TestSingletonAndConvenience:
    """Tests for singleton and convenience functions."""

    def test_get_work_history_singleton(self):
        """Test that get_work_history returns singleton."""
        import src.core.work_history as module
        module._history_instance = None

        history1 = get_work_history()
        history2 = get_work_history()

        assert history1 is history2

    def test_record_phase_completion_convenience(self, temp_history_file):
        """Test the record_phase_completion convenience function."""
        import src.core.work_history as module

        mock_history = MagicMock()
        mock_history.record_completion.return_value = True

        with patch.object(module, '_history_instance', mock_history):
            result = record_phase_completion("Agent", "1.1", "project", {"key": "value"})

        mock_history.record_completion.assert_called_once_with("Agent", "1.1", "project", {"key": "value"})
        assert result is True

    def test_get_agent_completed_phases_convenience(self, temp_history_file):
        """Test the get_agent_completed_phases convenience function."""
        import src.core.work_history as module

        mock_history = MagicMock()
        mock_history.get_completed_phases.return_value = ["1.1", "1.2"]

        with patch.object(module, '_history_instance', mock_history):
            result = get_agent_completed_phases("Agent", "project")

        mock_history.get_completed_phases.assert_called_once_with("Agent", "project")
        assert result == ["1.1", "1.2"]


class TestEdgeCases:
    """Tests for edge cases."""

    def test_record_completion_creates_nested_structure(self, temp_history_file):
        """Test that record_completion creates all nested structures."""
        history = WorkHistory(config_path=temp_history_file, project_id="test")

        # First record - creates all structure
        history.record_completion("NewAgent", "1.1")

        # Verify structure exists
        assert "NewAgent" in history.data["agents"]
        assert "projects" in history.data["agents"]["NewAgent"]
        assert "test" in history.data["agents"]["NewAgent"]["projects"]
        assert "completed" in history.data["agents"]["NewAgent"]["projects"]["test"]

    def test_multiple_projects_same_agent(self, temp_history_file):
        """Test recording completions across multiple projects for same agent."""
        history = WorkHistory(config_path=temp_history_file, project_id="default")

        history.record_completion("Agent", "1.1", project_id="project_a")
        history.record_completion("Agent", "2.1", project_id="project_b")
        history.record_completion("Agent", "1.2", project_id="project_a")

        phases_a = history.get_completed_phases("Agent", project_id="project_a")
        phases_b = history.get_completed_phases("Agent", project_id="project_b")

        assert phases_a == ["1.1", "1.2"]
        assert phases_b == ["2.1"]
