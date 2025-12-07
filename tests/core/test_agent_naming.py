"""Tests for agent naming system."""

import json
import warnings

import pytest

from src.core.agent_naming import AgentNaming
from src.core import work_history


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
    """Tests for agent experience tracking (completed phases).

    NOTE: The completed_phases methods in AgentNaming are deprecated.
    They now delegate to work_history module. These tests verify
    backwards compatibility and proper deprecation warnings.
    """

    @pytest.fixture
    def naming_with_agents(self, tmp_path):
        """Create config with agents and work history."""
        # Reset work_history singleton to use test path
        work_history._history_instance = None

        # Create agent_names.json (identity only - no completed_phases)
        config_file = tmp_path / "agent_names.json"
        config_file.write_text(json.dumps({
            "name_pools": {"default": ["Alpha", "Beta"]},
            "assigned_names": {
                "agent-1": {
                    "name": "Aria",
                    "role": "coder",
                    "claimed_at": "2025-01-01T12:00:00"
                },
                "agent-2": {
                    "name": "Atlas",
                    "role": "coder",
                    "claimed_at": "2025-01-01T13:00:00"
                }
            },
            "naming_config": {
                "persistent": True
            }
        }))

        # Create work_history.json for experience data
        work_history_file = tmp_path / "work_history.json"
        work_history_file.write_text(json.dumps({
            "agents": {
                "Aria": {
                    "projects": {
                        "test_project": {
                            "completed": [
                                {"phase_id": "1.1", "completed_at": "2025-01-01T12:00:00"},
                                {"phase_id": "1.2", "completed_at": "2025-01-01T12:30:00"}
                            ]
                        }
                    }
                }
            },
            "last_updated": "2025-01-01T12:30:00"
        }))

        # Use the test work_history file
        work_history._history_instance = work_history.WorkHistory(
            config_path=work_history_file,
            project_id="test_project"
        )

        return AgentNaming(config_file, project_id="test_project")

    def test_get_completed_phases(self, naming_with_agents):
        """Test getting completed phases for an agent (deprecated method)."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            phases = naming_with_agents.get_completed_phases("Aria")
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()
        assert phases == ["1.1", "1.2"]

    def test_get_completed_phases_none(self, naming_with_agents):
        """Test getting completed phases for agent with no completions."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            phases = naming_with_agents.get_completed_phases("Atlas")
        assert phases == []

    def test_get_completed_phases_unknown_agent(self, naming_with_agents):
        """Test getting completed phases for unknown agent."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            phases = naming_with_agents.get_completed_phases("Unknown")
        assert phases == []

    def test_record_completed_phase(self, naming_with_agents):
        """Test recording a completed phase (deprecated method)."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = naming_with_agents.record_completed_phase("Atlas", "2.1")
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
        assert result is True

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            phases = naming_with_agents.get_completed_phases("Atlas")
        assert "2.1" in phases

    def test_record_completed_phase_no_duplicates(self, naming_with_agents):
        """Test that duplicate phases aren't recorded."""
        # 1.1 is already in Aria's completed phases
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            naming_with_agents.record_completed_phase("Aria", "1.1")
            phases = naming_with_agents.get_completed_phases("Aria")
        assert phases.count("1.1") == 1

    def test_record_completed_phase_unknown_agent(self, naming_with_agents):
        """Test recording for unknown agent creates new entry in work_history.

        NOTE: Unlike the old behavior which returned False for unknown agents,
        work_history creates new entries for any agent name (returns True).
        """
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = naming_with_agents.record_completed_phase("NewAgent", "2.1")
        # work_history creates entries for new agents
        assert result is True

    def test_get_agent_experience(self, naming_with_agents):
        """Test getting all agents' experience (deprecated method)."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            experience = naming_with_agents.get_agent_experience()
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
        assert "Aria" in experience
        assert experience["Aria"] == ["1.1", "1.2"]

    def test_experience_persists(self, tmp_path):
        """Test that recorded experience persists to file."""
        # Reset work_history singleton
        work_history._history_instance = None

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

        # Create empty work_history
        work_history_file = tmp_path / "work_history.json"
        work_history_file.write_text(json.dumps({
            "agents": {},
            "last_updated": None
        }))
        work_history._history_instance = work_history.WorkHistory(
            config_path=work_history_file,
            project_id="test_project"
        )

        # Record a phase
        naming1 = AgentNaming(config_file, project_id="test_project")
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            naming1.record_completed_phase("Test", "3.1")

        # Reset and reload to verify persistence
        work_history._history_instance = work_history.WorkHistory(
            config_path=work_history_file,
            project_id="test_project"
        )
        naming2 = AgentNaming(config_file, project_id="test_project")
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            phases = naming2.get_completed_phases("Test")
        assert "3.1" in phases

    def test_experience_per_project(self, tmp_path):
        """Test that experience is tracked per project."""
        # Reset work_history singleton
        work_history._history_instance = None

        config_file = tmp_path / "agent_names.json"
        config_file.write_text(json.dumps({
            "name_pools": {"default": ["Alpha"]},
            "assigned_names": {
                "agent-1": {
                    "name": "Multi",
                    "role": "coder",
                    "claimed_at": "2025-01-01T12:00:00"
                }
            },
            "naming_config": {"persistent": True}
        }))

        # Create work_history with multi-project data
        work_history_file = tmp_path / "work_history.json"
        work_history_file.write_text(json.dumps({
            "agents": {
                "Multi": {
                    "projects": {
                        "project_a": {
                            "completed": [
                                {"phase_id": "1.1", "completed_at": "2025-01-01T12:00:00"},
                                {"phase_id": "1.2", "completed_at": "2025-01-01T12:30:00"}
                            ]
                        },
                        "project_b": {
                            "completed": [
                                {"phase_id": "2.1", "completed_at": "2025-01-01T13:00:00"}
                            ]
                        }
                    }
                }
            },
            "last_updated": "2025-01-01T13:00:00"
        }))

        # Use project_a context
        work_history._history_instance = work_history.WorkHistory(
            config_path=work_history_file,
            project_id="project_a"
        )
        naming_a = AgentNaming(config_file, project_id="project_a")
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            phases_a = naming_a.get_completed_phases("Multi")
        assert phases_a == ["1.1", "1.2"]

        # Use project_b context
        work_history._history_instance = work_history.WorkHistory(
            config_path=work_history_file,
            project_id="project_b"
        )
        naming_b = AgentNaming(config_file, project_id="project_b")
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            phases_b = naming_b.get_completed_phases("Multi")
        assert phases_b == ["2.1"]

        # Add a phase to project_b
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            naming_b.record_completed_phase("Multi", "2.2")
            phases_b_updated = naming_b.get_completed_phases("Multi")
        assert "2.1" in phases_b_updated
        assert "2.2" in phases_b_updated

        # Project A should remain unchanged
        work_history._history_instance = work_history.WorkHistory(
            config_path=work_history_file,
            project_id="project_a"
        )
        naming_a_fresh = AgentNaming(config_file, project_id="project_a")
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            phases_a_fresh = naming_a_fresh.get_completed_phases("Multi")
        assert phases_a_fresh == ["1.1", "1.2"]


class TestClaimNameFromPool:
    """Tests for claim_name_from_pool (legacy function)."""

    @pytest.fixture
    def temp_config(self, tmp_path):
        """Create a temporary agent_names.json config."""
        config_file = tmp_path / "agent_names.json"
        config_file.write_text(json.dumps({
            "name_pools": {
                "coder": ["Ada", "Alan", "Grace"],
                "default": ["Alpha", "Beta", "Gamma"]
            },
            "assigned_names": {},
            "naming_config": {
                "format": "{name}-{role_suffix}",
                "allow_duplicates": False,
                "add_numeric_suffix_on_conflict": True,
                "persistent": True
            }
        }))
        return config_file

    def test_claim_from_pool_new_agent(self, temp_config):
        """Test claiming name from pool for new agent."""
        naming = AgentNaming(temp_config)
        name = naming.claim_name_from_pool("agent-1", "coder")
        assert name in ["Ada", "Alan", "Grace"]

    def test_claim_from_pool_preferred_name(self, temp_config):
        """Test claiming with preferred name."""
        naming = AgentNaming(temp_config)
        name = naming.claim_name_from_pool("agent-1", "coder", preferred_name="Ada")
        assert name == "Ada"

    def test_claim_from_pool_preferred_taken(self, temp_config):
        """Test claiming with taken preferred name adds suffix."""
        naming = AgentNaming(temp_config)
        naming.claim_name_from_pool("agent-1", "coder", preferred_name="Ada")
        name = naming.claim_name_from_pool("agent-2", "coder", preferred_name="Ada")
        assert name == "Ada-2"

    def test_claim_from_pool_existing_agent(self, temp_config):
        """Test claiming returns existing name for same agent."""
        naming = AgentNaming(temp_config)
        name1 = naming.claim_name_from_pool("agent-1", "coder", preferred_name="Ada")
        name2 = naming.claim_name_from_pool("agent-1", "coder", preferred_name="Grace")
        assert name1 == name2 == "Ada"

    def test_claim_from_pool_all_taken(self, tmp_path):
        """Test claiming when all pool names are taken."""
        config_file = tmp_path / "agent_names.json"
        config_file.write_text(json.dumps({
            "name_pools": {
                "default": ["Alpha"]
            },
            "assigned_names": {
                "agent-1": {"name": "Alpha", "role": "default", "claimed_at": "2025-01-01T00:00:00"}
            },
            "naming_config": {
                "add_numeric_suffix_on_conflict": True,
                "persistent": True
            }
        }))
        naming = AgentNaming(config_file)
        name = naming.claim_name_from_pool("agent-2", "default")
        assert name == "Alpha-2"

    def test_claim_from_pool_no_suffix(self, tmp_path):
        """Test claiming without suffix option."""
        config_file = tmp_path / "agent_names.json"
        config_file.write_text(json.dumps({
            "name_pools": {
                "default": ["Alpha", "Beta"]
            },
            "assigned_names": {
                "agent-1": {"name": "Alpha", "role": "default", "claimed_at": "2025-01-01T00:00:00"}
            },
            "naming_config": {
                "add_numeric_suffix_on_conflict": False,
                "persistent": True
            }
        }))
        naming = AgentNaming(config_file)
        name = naming.claim_name_from_pool("agent-2", "default", preferred_name="Alpha")
        # Should pick from available pool names instead
        assert name == "Beta"


class TestReleaseNameAndAvailability:
    """Tests for release_name and get_available_names."""

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
                "agent-1": {"name": "Ada", "role": "coder", "claimed_at": "2025-01-01T00:00:00"},
                "agent-2": {"name": "Alan", "role": "coder", "claimed_at": "2025-01-01T00:00:00"}
            },
            "naming_config": {
                "persistent": True
            }
        }))
        return config_file

    def test_release_name_success(self, temp_config):
        """Test successfully releasing a name."""
        naming = AgentNaming(temp_config)
        result = naming.release_name("agent-1")
        assert result is True
        assert naming.get_name("agent-1") is None
        assert naming.is_name_available("Ada") is True

    def test_release_name_nonexistent(self, temp_config):
        """Test releasing name for nonexistent agent."""
        naming = AgentNaming(temp_config)
        result = naming.release_name("nonexistent")
        assert result is False

    def test_get_available_names(self, temp_config):
        """Test getting available names for a role."""
        naming = AgentNaming(temp_config)
        available = naming.get_available_names("coder")
        assert "Grace" in available
        assert "Ada" not in available
        assert "Alan" not in available

    def test_get_available_names_default_role(self, temp_config):
        """Test getting available names for default role."""
        naming = AgentNaming(temp_config)
        available = naming.get_available_names("default")
        assert set(available) == {"Alpha", "Beta", "Gamma"}

    def test_get_available_names_unknown_role(self, temp_config):
        """Test getting available names for unknown role falls back to default."""
        naming = AgentNaming(temp_config)
        available = naming.get_available_names("unknown_role")
        assert set(available) == {"Alpha", "Beta", "Gamma"}


class TestMakeUnique:
    """Tests for _make_unique helper."""

    @pytest.fixture
    def temp_config(self, tmp_path):
        """Create a minimal config."""
        config_file = tmp_path / "agent_names.json"
        config_file.write_text(json.dumps({
            "name_pools": {"default": ["Alpha"]},
            "assigned_names": {},
            "naming_config": {"persistent": True}
        }))
        return config_file

    def test_make_unique_name_available(self, temp_config):
        """Test _make_unique returns name if available."""
        naming = AgentNaming(temp_config)
        result = naming._make_unique("Alpha", set())
        assert result == "Alpha"

    def test_make_unique_adds_suffix(self, temp_config):
        """Test _make_unique adds suffix when name taken."""
        naming = AgentNaming(temp_config)
        result = naming._make_unique("Alpha", {"Alpha"})
        assert result == "Alpha-2"

    def test_make_unique_increments_suffix(self, temp_config):
        """Test _make_unique increments suffix for multiple conflicts."""
        naming = AgentNaming(temp_config)
        assigned = {"Alpha", "Alpha-2", "Alpha-3"}
        result = naming._make_unique("Alpha", assigned)
        assert result == "Alpha-4"


class TestConfigPathAndErrors:
    """Tests for config path handling and error cases."""

    def test_default_config_path(self):
        """Test default config path resolves correctly."""
        naming = AgentNaming()
        assert naming.config_path.name == "agent_names.json"
        assert "config" in str(naming.config_path)

    def test_config_file_not_found(self, tmp_path):
        """Test FileNotFoundError when config doesn't exist."""
        config_file = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError) as exc_info:
            AgentNaming(config_file)
        assert "Agent naming config not found" in str(exc_info.value)


class TestGetAllExperience:
    """Tests for get_all_experience deprecated method."""

    @pytest.fixture
    def naming_with_experience(self, tmp_path):
        """Create naming with work history."""
        work_history._history_instance = None

        config_file = tmp_path / "agent_names.json"
        config_file.write_text(json.dumps({
            "name_pools": {"default": ["Alpha"]},
            "assigned_names": {},
            "naming_config": {"persistent": True}
        }))

        work_history_file = tmp_path / "work_history.json"
        work_history_file.write_text(json.dumps({
            "agents": {
                "Agent1": {
                    "projects": {
                        "project_a": {"completed": [{"phase_id": "1.1", "completed_at": "2025-01-01T00:00:00"}]},
                        "project_b": {"completed": [{"phase_id": "2.1", "completed_at": "2025-01-01T00:00:00"}]}
                    }
                }
            },
            "last_updated": "2025-01-01T00:00:00"
        }))

        work_history._history_instance = work_history.WorkHistory(
            config_path=work_history_file,
            project_id="test"
        )

        return AgentNaming(config_file)

    def test_get_all_experience(self, naming_with_experience):
        """Test get_all_experience deprecated method."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = naming_with_experience.get_all_experience()
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
        assert "Agent1" in result
        assert "project_a" in result["Agent1"]
        assert "project_b" in result["Agent1"]


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @pytest.fixture
    def reset_singleton(self, tmp_path):
        """Reset the singleton and provide test config."""
        import src.core.agent_naming as module
        module._naming_instance = None

        config_file = tmp_path / "agent_names.json"
        config_file.write_text(json.dumps({
            "name_pools": {"default": ["Alpha", "Beta"]},
            "assigned_names": {
                "agent-1": {"name": "Taken", "role": "default", "claimed_at": "2025-01-01T00:00:00"}
            },
            "naming_config": {"persistent": True}
        }))

        # Set default path to test file
        original_init = AgentNaming.__init__

        def patched_init(self, config_path=None, project_id=None):
            original_init(self, config_path or config_file, project_id)

        module.AgentNaming.__init__ = patched_init
        yield
        module.AgentNaming.__init__ = original_init
        module._naming_instance = None

    def test_get_naming_singleton(self, reset_singleton):
        """Test get_naming returns singleton."""
        import src.core.agent_naming as module

        naming1 = module.get_naming()
        naming2 = module.get_naming()
        assert naming1 is naming2

    def test_claim_agent_name_convenience(self, reset_singleton):
        """Test claim_agent_name convenience function."""
        import src.core.agent_naming as module

        success, result = module.claim_agent_name("agent-new", "NewName", "default")
        assert success is True
        assert result == "NewName"

    def test_is_name_available_convenience(self, reset_singleton):
        """Test is_name_available convenience function."""
        import src.core.agent_naming as module

        assert module.is_name_available("NewName") is True
        assert module.is_name_available("Taken") is False

    def test_get_taken_names_convenience(self, reset_singleton):
        """Test get_taken_names convenience function."""
        import src.core.agent_naming as module

        taken = module.get_taken_names()
        assert "Taken" in taken


class TestAgentReuseScoring:
    """Tests for agent reuse based on experience."""

    @pytest.fixture
    def experienced_agents(self, tmp_path):
        """Create agents with varied experience."""
        # Reset work_history singleton
        work_history._history_instance = None

        config_file = tmp_path / "agent_names.json"
        config_file.write_text(json.dumps({
            "name_pools": {"default": ["Alpha"]},
            "assigned_names": {
                "agent-1": {
                    "name": "Aria",
                    "role": "coder",
                    "claimed_at": "2025-01-01T12:00:00"
                },
                "agent-2": {
                    "name": "Atlas",
                    "role": "coder",
                    "claimed_at": "2025-01-01T13:00:00"
                },
                "agent-3": {
                    "name": "Nexus",
                    "role": "coder",
                    "claimed_at": "2025-01-01T14:00:00"
                }
            },
            "naming_config": {"persistent": True}
        }))

        # Create work_history with experience data
        work_history_file = tmp_path / "work_history.json"
        work_history_file.write_text(json.dumps({
            "agents": {
                "Aria": {
                    "projects": {
                        "test_project": {
                            "completed": [
                                {"phase_id": "1.1", "completed_at": "2025-01-01T12:00:00"},
                                {"phase_id": "1.2", "completed_at": "2025-01-01T12:30:00"},
                                {"phase_id": "1.3", "completed_at": "2025-01-01T13:00:00"}
                            ]
                        }
                    }
                },
                "Atlas": {
                    "projects": {
                        "test_project": {
                            "completed": [
                                {"phase_id": "2.1", "completed_at": "2025-01-01T13:00:00"},
                                {"phase_id": "2.2", "completed_at": "2025-01-01T13:30:00"}
                            ]
                        }
                    }
                },
                "Nexus": {
                    "projects": {}
                }
            },
            "last_updated": "2025-01-01T13:30:00"
        }))

        work_history._history_instance = work_history.WorkHistory(
            config_path=work_history_file,
            project_id="test_project"
        )

        return AgentNaming(config_file, project_id="test_project")

    def test_experience_by_batch(self, experienced_agents):
        """Test filtering experience by batch number."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            experience = experienced_agents.get_agent_experience()

        # Aria has 3 phases in batch 1
        aria_batch1 = [p for p in experience["Aria"] if p.startswith("1.")]
        assert len(aria_batch1) == 3

        # Atlas has 2 phases in batch 2
        atlas_batch2 = [p for p in experience["Atlas"] if p.startswith("2.")]
        assert len(atlas_batch2) == 2

        # Nexus has no experience
        assert len(experience.get("Nexus", [])) == 0

    def test_find_most_experienced_for_batch(self, experienced_agents):
        """Test finding most experienced agent for a batch."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
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
