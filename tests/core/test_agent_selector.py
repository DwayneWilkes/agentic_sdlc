"""Tests for agent selector module."""

import json

import pytest

from src.core.agent_selector import (
    AgentSelector,
    get_agent_id_for_phase,
    get_selector,
    select_agent_for_phase,
)


class TestAgentSelector:
    """Tests for AgentSelector class."""

    @pytest.fixture
    def temp_config(self, tmp_path):
        """Create temporary config files."""
        agent_names = tmp_path / "agent_names.json"
        agent_names.write_text(json.dumps({
            "assigned_names": {
                "agent-1": {"name": "Nova", "role": "coder"},
                "agent-2": {"name": "Atlas", "role": "coder"},
                "agent-3": {"name": "Nexus", "role": "coder"},
                "agent-4": {"name": "Sage", "role": "coder"},
            }
        }))

        work_history = tmp_path / "work_history.json"
        work_history.write_text(json.dumps({
            "agents": {
                "Nova": {
                    "projects": {
                        "agentic_sdlc": {
                            "completed": [
                                {"phase_id": "1.1", "completed_at": "2025-12-05"},
                                {"phase_id": "1.2", "completed_at": "2025-12-05"},
                            ]
                        }
                    }
                },
                "Atlas": {
                    "projects": {
                        "agentic_sdlc": {
                            "completed": [
                                {"phase_id": "2.1", "completed_at": "2025-12-05"},
                                {"phase_id": "2.2", "completed_at": "2025-12-05"},
                                {"phase_id": "2.3", "completed_at": "2025-12-06"},
                            ]
                        }
                    }
                },
            }
        }))

        return agent_names, work_history

    def test_get_available_agents(self, temp_config):
        """Test getting list of available agents."""
        agent_names, work_history = temp_config
        selector = AgentSelector(agent_names, work_history)

        agents = selector.get_available_agents()

        assert len(agents) == 4
        names = {a["name"] for a in agents}
        assert names == {"Nova", "Atlas", "Nexus", "Sage"}

    def test_get_available_agents_empty(self, tmp_path):
        """Test with no registered agents."""
        agent_names = tmp_path / "agent_names.json"
        agent_names.write_text(json.dumps({"assigned_names": {}}))

        selector = AgentSelector(agent_names, tmp_path / "work_history.json")
        agents = selector.get_available_agents()

        assert agents == []

    def test_get_agent_experience(self, temp_config):
        """Test getting agent experience."""
        agent_names, work_history = temp_config
        selector = AgentSelector(agent_names, work_history)

        experience = selector.get_agent_experience("Nova")
        assert experience == ["1.1", "1.2"]

        experience = selector.get_agent_experience("Atlas")
        assert experience == ["2.1", "2.2", "2.3"]

    def test_get_agent_experience_no_history(self, temp_config):
        """Test agent with no work history."""
        agent_names, work_history = temp_config
        selector = AgentSelector(agent_names, work_history)

        experience = selector.get_agent_experience("Nexus")
        assert experience == []

    def test_calculate_affinity_same_batch(self, temp_config):
        """Test affinity calculation for same batch."""
        agent_names, work_history = temp_config
        selector = AgentSelector(agent_names, work_history)

        # Atlas has experience in batch 2, should have high affinity for 2.4
        affinity = selector.calculate_affinity("Atlas", "2.4")
        assert affinity > 0.5

        # Nova has experience in batch 1, should have lower affinity for 2.4
        affinity_nova = selector.calculate_affinity("Nova", "2.4")
        assert affinity_nova < affinity

    def test_calculate_affinity_adjacent_batch(self, temp_config):
        """Test affinity for adjacent batch."""
        agent_names, work_history = temp_config
        selector = AgentSelector(agent_names, work_history)

        # Nova has batch 1 experience, should have some affinity for batch 2
        affinity = selector.calculate_affinity("Nova", "2.1")
        assert affinity > 0.1  # More than base

    def test_calculate_affinity_no_experience(self, temp_config):
        """Test affinity for agent with no experience."""
        agent_names, work_history = temp_config
        selector = AgentSelector(agent_names, work_history)

        affinity = selector.calculate_affinity("Nexus", "5.1")
        assert affinity == 0.1  # Base score

    def test_select_agent_prefers_experience(self, temp_config):
        """Test that selector prefers agents with relevant experience."""
        agent_names, work_history = temp_config
        selector = AgentSelector(agent_names, work_history)

        # For batch 2 work, Atlas should be preferred
        selected = selector.select_agent("2.4")
        assert selected is not None
        assert selected["name"] == "Atlas"

        # For batch 1 work, Nova should be preferred
        selected = selector.select_agent("1.3")
        assert selected is not None
        assert selected["name"] == "Nova"

    def test_select_agent_no_agents(self, tmp_path):
        """Test selection with no available agents."""
        agent_names = tmp_path / "agent_names.json"
        agent_names.write_text(json.dumps({"assigned_names": {}}))

        selector = AgentSelector(agent_names, tmp_path / "work_history.json")
        selected = selector.select_agent("1.1")

        assert selected is None

    def test_select_agent_id(self, temp_config):
        """Test selecting just agent ID."""
        agent_names, work_history = temp_config
        selector = AgentSelector(agent_names, work_history)

        agent_id = selector.select_agent_id("2.4")
        assert agent_id == "agent-2"  # Atlas

    def test_should_hire_new_agent_no_agents(self, tmp_path):
        """Test hire decision with no agents."""
        agent_names = tmp_path / "agent_names.json"
        agent_names.write_text(json.dumps({"assigned_names": {}}))

        selector = AgentSelector(agent_names, tmp_path / "work_history.json")
        should_hire = selector.should_hire_new_agent("1.1")

        assert should_hire is True

    def test_should_hire_new_agent_low_affinity(self, tmp_path):
        """Test hire decision with low affinity agents."""
        agent_names = tmp_path / "agent_names.json"
        agent_names.write_text(json.dumps({
            "assigned_names": {
                "agent-1": {"name": "NewAgent", "role": "coder"},
            }
        }))
        work_history = tmp_path / "work_history.json"
        work_history.write_text(json.dumps({"agents": {}}))

        selector = AgentSelector(agent_names, work_history)

        # With very high threshold, should want to hire new
        should_hire = selector.should_hire_new_agent("1.1", threshold=0.5)
        assert should_hire is True

    def test_should_hire_new_agent_good_match(self, temp_config):
        """Test hire decision with good existing match."""
        agent_names, work_history = temp_config
        selector = AgentSelector(agent_names, work_history)

        # Atlas has good experience for batch 2, shouldn't hire new
        should_hire = selector.should_hire_new_agent("2.4")
        assert should_hire is False


class TestAgentSelectorMissingFiles:
    """Tests for missing config files."""

    def test_missing_agent_names(self, tmp_path):
        """Test with missing agent_names.json."""
        selector = AgentSelector(
            tmp_path / "nonexistent.json",
            tmp_path / "work_history.json"
        )
        agents = selector.get_available_agents()
        assert agents == []

    def test_missing_work_history(self, tmp_path):
        """Test with missing work_history.json."""
        agent_names = tmp_path / "agent_names.json"
        agent_names.write_text(json.dumps({
            "assigned_names": {
                "agent-1": {"name": "Test", "role": "coder"},
            }
        }))

        selector = AgentSelector(agent_names, tmp_path / "nonexistent.json")
        experience = selector.get_agent_experience("Test")
        assert experience == []


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_selector_singleton(self):
        """Test that get_selector returns singleton."""
        import src.core.agent_selector as module
        module._selector_instance = None

        selector1 = get_selector()
        selector2 = get_selector()
        assert selector1 is selector2

        module._selector_instance = None  # Reset

    def test_select_agent_for_phase(self, tmp_path, monkeypatch):
        """Test convenience function."""
        import src.core.agent_selector as module

        agent_names = tmp_path / "agent_names.json"
        agent_names.write_text(json.dumps({
            "assigned_names": {
                "agent-1": {"name": "Test", "role": "coder"},
            }
        }))

        module._selector_instance = AgentSelector(
            agent_names,
            tmp_path / "work_history.json"
        )

        agent = select_agent_for_phase("1.1")
        assert agent is not None
        assert agent["name"] == "Test"

        module._selector_instance = None  # Reset

    def test_get_agent_id_for_phase(self, tmp_path):
        """Test convenience function for agent ID."""
        import src.core.agent_selector as module

        agent_names = tmp_path / "agent_names.json"
        agent_names.write_text(json.dumps({
            "assigned_names": {
                "agent-1": {"name": "Test", "role": "coder"},
            }
        }))

        module._selector_instance = AgentSelector(
            agent_names,
            tmp_path / "work_history.json"
        )

        agent_id = get_agent_id_for_phase("1.1")
        assert agent_id == "agent-1"

        module._selector_instance = None  # Reset
