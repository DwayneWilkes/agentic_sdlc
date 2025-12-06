"""Tests for agent naming system."""

import json

import pytest

from src.core.agent_naming import AgentNaming


class TestAgentNaming:
    """Tests for AgentNaming class."""

    @pytest.fixture
    def temp_config(self, tmp_path):
        """Create a temporary agent_names.json config."""
        config_file = tmp_path / "agent_names.json"
        config_file.write_text(json.dumps({
            "name_pools": {
                "coder": ["Ada", "Alan", "Grace"],
                "default": ["Alpha", "Beta", "Gamma"]
            },
            "assigned_names": {
                "agent-1": {
                    "name": "Aria",
                    "role": "coder",
                    "claimed_at": "2025-01-01T12:00:00",
                    "completed_phases": ["1.1", "1.2"]
                },
                "agent-2": {
                    "name": "Atlas",
                    "role": "coder",
                    "claimed_at": "2025-01-01T13:00:00"
                }
            },
            "naming_config": {
                "format": "{name}-{role_suffix}",
                "allow_duplicates": False,
                "add_numeric_suffix_on_conflict": True,
                "persistent": True
            }
        }))
        return config_file

    def test_is_name_available(self, temp_config):
        """Test checking name availability."""
        naming = AgentNaming(temp_config)
        assert naming.is_name_available("NewName") is True
        assert naming.is_name_available("Aria") is False
        assert naming.is_name_available("Atlas") is False

    def test_get_taken_names(self, temp_config):
        """Test getting list of taken names."""
        naming = AgentNaming(temp_config)
        taken = naming.get_taken_names()
        assert "Aria" in taken
        assert "Atlas" in taken
        assert len(taken) == 2

    def test_claim_name_success(self, temp_config):
        """Test successfully claiming a new name."""
        naming = AgentNaming(temp_config)
        success, result = naming.claim_name("agent-3", "NewAgent", "coder")
        assert success is True
        assert result == "NewAgent"
        assert naming.get_name("agent-3") == "NewAgent"

    def test_claim_name_already_taken(self, temp_config):
        """Test claiming an already taken name."""
        naming = AgentNaming(temp_config)
        success, result = naming.claim_name("agent-3", "Aria", "coder")
        assert success is False
        assert "already taken" in result

    def test_claim_name_same_agent(self, temp_config):
        """Test agent reclaiming their own name."""
        naming = AgentNaming(temp_config)
        success, result = naming.claim_name("agent-1", "Aria", "coder")
        assert success is True
        assert result == "Aria"

    def test_get_name(self, temp_config):
        """Test getting name by agent ID."""
        naming = AgentNaming(temp_config)
        assert naming.get_name("agent-1") == "Aria"
        assert naming.get_name("agent-2") == "Atlas"
        assert naming.get_name("nonexistent") is None

    def test_get_agent_id(self, temp_config):
        """Test reverse lookup by personal name."""
        naming = AgentNaming(temp_config)
        assert naming.get_agent_id("Aria") == "agent-1"
        assert naming.get_agent_id("Atlas") == "agent-2"
        assert naming.get_agent_id("Nonexistent") is None

    def test_list_assigned_names(self, temp_config):
        """Test listing all assigned names."""
        naming = AgentNaming(temp_config)
        assigned = naming.list_assigned_names()
        assert "agent-1" in assigned
        assert "agent-2" in assigned
        assert assigned["agent-1"]["name"] == "Aria"


class TestAgentExperienceTracking:
    """Tests for agent experience tracking (completed phases)."""

    @pytest.fixture
    def naming_with_agents(self, tmp_path):
        """Create config with agents that have completed phases."""
        config_file = tmp_path / "agent_names.json"
        config_file.write_text(json.dumps({
            "name_pools": {"default": ["Alpha", "Beta"]},
            "assigned_names": {
                "agent-1": {
                    "name": "Aria",
                    "role": "coder",
                    "claimed_at": "2025-01-01T12:00:00",
                    "completed_phases": {
                        "test_project": ["1.1", "1.2"]
                    }
                },
                "agent-2": {
                    "name": "Atlas",
                    "role": "coder",
                    "claimed_at": "2025-01-01T13:00:00"
                    # No completed_phases yet
                }
            },
            "naming_config": {
                "persistent": True
            }
        }))
        return AgentNaming(config_file, project_id="test_project")

    def test_get_completed_phases(self, naming_with_agents):
        """Test getting completed phases for an agent."""
        phases = naming_with_agents.get_completed_phases("Aria")
        assert phases == ["1.1", "1.2"]

    def test_get_completed_phases_none(self, naming_with_agents):
        """Test getting completed phases for agent with no completions."""
        phases = naming_with_agents.get_completed_phases("Atlas")
        assert phases == []

    def test_get_completed_phases_unknown_agent(self, naming_with_agents):
        """Test getting completed phases for unknown agent."""
        phases = naming_with_agents.get_completed_phases("Unknown")
        assert phases == []

    def test_record_completed_phase(self, naming_with_agents):
        """Test recording a completed phase."""
        result = naming_with_agents.record_completed_phase("Atlas", "2.1")
        assert result is True

        phases = naming_with_agents.get_completed_phases("Atlas")
        assert "2.1" in phases

    def test_record_completed_phase_no_duplicates(self, naming_with_agents):
        """Test that duplicate phases aren't recorded."""
        # 1.1 is already in Aria's completed phases
        naming_with_agents.record_completed_phase("Aria", "1.1")
        phases = naming_with_agents.get_completed_phases("Aria")
        assert phases.count("1.1") == 1

    def test_record_completed_phase_unknown_agent(self, naming_with_agents):
        """Test recording for unknown agent returns False."""
        result = naming_with_agents.record_completed_phase("Unknown", "2.1")
        assert result is False

    def test_get_agent_experience(self, naming_with_agents):
        """Test getting all agents' experience."""
        experience = naming_with_agents.get_agent_experience()
        assert "Aria" in experience
        assert "Atlas" in experience
        assert experience["Aria"] == ["1.1", "1.2"]
        assert experience["Atlas"] == []

    def test_experience_persists(self, tmp_path):
        """Test that recorded experience persists to file."""
        config_file = tmp_path / "agent_names.json"
        config_file.write_text(json.dumps({
            "name_pools": {"default": ["Alpha"]},
            "assigned_names": {
                "agent-1": {
                    "name": "Test",
                    "role": "coder",
                    "claimed_at": "2025-01-01T12:00:00"
                }
            },
            "naming_config": {"persistent": True}
        }))

        # Record a phase
        naming1 = AgentNaming(config_file, project_id="test_project")
        naming1.record_completed_phase("Test", "3.1")

        # Load fresh instance and verify persistence
        naming2 = AgentNaming(config_file, project_id="test_project")
        phases = naming2.get_completed_phases("Test")
        assert "3.1" in phases

    def test_experience_per_project(self, tmp_path):
        """Test that experience is tracked per project."""
        config_file = tmp_path / "agent_names.json"
        config_file.write_text(json.dumps({
            "name_pools": {"default": ["Alpha"]},
            "assigned_names": {
                "agent-1": {
                    "name": "Multi",
                    "role": "coder",
                    "claimed_at": "2025-01-01T12:00:00",
                    "completed_phases": {
                        "project_a": ["1.1", "1.2"],
                        "project_b": ["2.1"]
                    }
                }
            },
            "naming_config": {"persistent": True}
        }))

        naming_a = AgentNaming(config_file, project_id="project_a")
        naming_b = AgentNaming(config_file, project_id="project_b")

        assert naming_a.get_completed_phases("Multi") == ["1.1", "1.2"]
        assert naming_b.get_completed_phases("Multi") == ["2.1"]

        # Add a phase to project_b
        naming_b.record_completed_phase("Multi", "2.2")
        assert naming_b.get_completed_phases("Multi") == ["2.1", "2.2"]

        # Project A should remain unchanged
        naming_a_fresh = AgentNaming(config_file, project_id="project_a")
        assert naming_a_fresh.get_completed_phases("Multi") == ["1.1", "1.2"]


class TestAgentReuseScoring:
    """Tests for agent reuse based on experience."""

    @pytest.fixture
    def experienced_agents(self, tmp_path):
        """Create agents with varied experience."""
        config_file = tmp_path / "agent_names.json"
        config_file.write_text(json.dumps({
            "name_pools": {"default": ["Alpha"]},
            "assigned_names": {
                "agent-1": {
                    "name": "Aria",
                    "role": "coder",
                    "claimed_at": "2025-01-01T12:00:00",
                    "completed_phases": {
                        "test_project": ["1.1", "1.2", "1.3"]
                    }
                },
                "agent-2": {
                    "name": "Atlas",
                    "role": "coder",
                    "claimed_at": "2025-01-01T13:00:00",
                    "completed_phases": {
                        "test_project": ["2.1", "2.2"]
                    }
                },
                "agent-3": {
                    "name": "Nexus",
                    "role": "coder",
                    "claimed_at": "2025-01-01T14:00:00",
                    "completed_phases": {}
                }
            },
            "naming_config": {"persistent": True}
        }))
        return AgentNaming(config_file, project_id="test_project")

    def test_experience_by_batch(self, experienced_agents):
        """Test filtering experience by batch number."""
        experience = experienced_agents.get_agent_experience()

        # Aria has 3 phases in batch 1
        aria_batch1 = [p for p in experience["Aria"] if p.startswith("1.")]
        assert len(aria_batch1) == 3

        # Atlas has 2 phases in batch 2
        atlas_batch2 = [p for p in experience["Atlas"] if p.startswith("2.")]
        assert len(atlas_batch2) == 2

        # Nexus has no experience
        assert len(experience["Nexus"]) == 0

    def test_find_most_experienced_for_batch(self, experienced_agents):
        """Test finding most experienced agent for a batch."""
        experience = experienced_agents.get_agent_experience()

        # For batch 1 work, Aria should be preferred (3 phases in batch 1)
        batch1_scores = {}
        for name, phases in experience.items():
            batch1_phases = [p for p in phases if p.startswith("1.")]
            batch1_scores[name] = len(batch1_phases)

        best_for_batch1 = max(batch1_scores, key=batch1_scores.get)
        assert best_for_batch1 == "Aria"

        # For batch 2 work, Atlas should be preferred
        batch2_scores = {}
        for name, phases in experience.items():
            batch2_phases = [p for p in phases if p.startswith("2.")]
            batch2_scores[name] = len(batch2_phases)

        best_for_batch2 = max(batch2_scores, key=batch2_scores.get)
        assert best_for_batch2 == "Atlas"
