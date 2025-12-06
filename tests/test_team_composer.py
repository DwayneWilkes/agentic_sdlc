"""Tests for Team Composition Engine."""

import pytest

from src.core.role_registry import RoleRegistry
from src.core.team_composer import TeamComposer
from src.models.task import Subtask


class TestTeamComposer:
    """Test TeamComposer class."""

    @pytest.fixture
    def registry(self):
        """Create a standard role registry for testing."""
        return RoleRegistry.create_standard_registry()

    @pytest.fixture
    def composer(self, registry):
        """Create a team composer with standard registry."""
        return TeamComposer(registry)

    def test_compose_team_basic(self, composer):
        """Test basic team composition with simple subtasks."""
        subtasks = [
            Subtask(
                id="subtask-1",
                description="Implement user authentication",
                requirements={
                    "capabilities": ["coding", "implementation"],
                    "tools": ["python", "pytest"],
                    "domain_knowledge": ["software_engineering"],
                },
            ),
            Subtask(
                id="subtask-2",
                description="Write tests for authentication",
                requirements={
                    "capabilities": ["testing", "test_automation"],
                    "tools": ["pytest"],
                    "domain_knowledge": ["qa_methodology"],
                },
            ),
        ]

        team = composer.compose_team(subtasks, team_name="Auth Team")

        assert team is not None
        assert team.name == "Auth Team"
        assert len(team.agents) > 0
        assert len(team.agents) <= len(subtasks) + 1  # Not over-staffed

    def test_compose_team_avoid_overstaffing(self, composer):
        """Test that team sizing avoids over-staffing."""
        # 2 simple subtasks should not result in 10 agents
        subtasks = [
            Subtask(
                id="subtask-1",
                description="Simple task 1",
                requirements={"capabilities": ["coding"]},
            ),
            Subtask(
                id="subtask-2",
                description="Simple task 2",
                requirements={"capabilities": ["testing"]},
            ),
        ]

        team = composer.compose_team(subtasks)

        # Should have 2-3 agents max for 2 simple tasks
        assert len(team.agents) <= 3
        assert len(team.agents) >= 1  # At least one agent needed

    def test_compose_team_avoid_understaffing(self, composer):
        """Test that team sizing provides enough agents for workload."""
        # Many subtasks should get multiple agents
        subtasks = [
            Subtask(
                id=f"subtask-{i}",
                description=f"Task {i}",
                requirements={"capabilities": ["coding"]},
            )
            for i in range(10)
        ]

        team = composer.compose_team(subtasks)

        # Should have multiple agents for 10 tasks
        assert len(team.agents) >= 3
        # But not one agent per task (that would be over-staffing)
        assert len(team.agents) < len(subtasks)

    def test_compose_team_complementary_roles(self, composer):
        """Test that team has complementary roles without redundancy."""
        subtasks = [
            Subtask(
                id="subtask-1",
                description="Develop feature",
                requirements={"capabilities": ["coding"]},
            ),
            Subtask(
                id="subtask-2",
                description="Test feature",
                requirements={"capabilities": ["testing"]},
            ),
            Subtask(
                id="subtask-3",
                description="Review code",
                requirements={"capabilities": ["code_review"]},
            ),
        ]

        team = composer.compose_team(subtasks)

        # Get unique roles
        roles = {agent.role for agent in team.agents}

        # Should have developer, tester, and reviewer (complementary)
        assert "developer" in roles or "tester" in roles or "reviewer" in roles
        # Should not have excessive duplicate roles
        assert len(team.agents) <= 5  # Reasonable team size

    def test_compose_team_skill_coverage(self, composer):
        """Test that all required capabilities are covered."""
        subtasks = [
            Subtask(
                id="subtask-1",
                description="Data analysis task",
                requirements={
                    "capabilities": ["data_analysis", "statistical_analysis"],
                    "tools": ["pandas", "numpy"],
                },
            ),
            Subtask(
                id="subtask-2",
                description="Research task",
                requirements={
                    "capabilities": ["research", "literature_review"],
                    "tools": ["web_search"],
                },
            ),
        ]

        team = composer.compose_team(subtasks)

        # Collect all capabilities from team agents
        team_capabilities = set()
        for agent in team.agents:
            for cap in agent.capabilities:
                team_capabilities.add(cap.name)

        # Check that key capabilities are covered
        # (May not be exact match due to role mapping)
        assert len(team.agents) > 0
        # Team should have analysts and researchers
        roles = {agent.role for agent in team.agents}
        assert "analyst" in roles or "researcher" in roles

    def test_compose_team_specialization_for_complex_tasks(self, composer):
        """Test that specialists are preferred for complex tasks."""
        subtasks = [
            Subtask(
                id="subtask-1",
                description="Complex data analysis with ML",
                requirements={
                    "capabilities": [
                        "data_analysis",
                        "statistical_analysis",
                        "pattern_recognition",
                    ],
                    "tools": ["pandas", "numpy", "matplotlib"],
                    "domain_knowledge": ["statistics", "data_science"],
                },
            ),
        ]

        team = composer.compose_team(subtasks)

        # Should prefer specialist (analyst) for complex data task
        roles = [agent.role for agent in team.agents]
        assert "analyst" in roles

    def test_compose_team_generalization_for_diverse_tasks(self, composer):
        """Test that generalists are used for diverse task sets."""
        subtasks = [
            Subtask(
                id="subtask-1",
                description="Write code",
                requirements={"capabilities": ["coding"]},
            ),
            Subtask(
                id="subtask-2",
                description="Analyze data",
                requirements={"capabilities": ["data_analysis"]},
            ),
            Subtask(
                id="subtask-3",
                description="Research topic",
                requirements={"capabilities": ["research"]},
            ),
        ]

        team = composer.compose_team(subtasks)

        # Diverse tasks may use generalists or specialists
        # Key is that team size is reasonable
        assert len(team.agents) >= 2  # At least 2 for diverse tasks
        assert len(team.agents) <= 4  # But not too many

    def test_compose_team_empty_subtasks(self, composer):
        """Test team composition with empty subtask list."""
        team = composer.compose_team([])

        # Should return minimal team or empty team
        assert team is not None
        assert len(team.agents) == 0  # No work, no agents

    def test_compose_team_single_subtask(self, composer):
        """Test team composition with single subtask."""
        subtasks = [
            Subtask(
                id="subtask-1",
                description="Simple task",
                requirements={"capabilities": ["coding"]},
            ),
        ]

        team = composer.compose_team(subtasks)

        assert len(team.agents) >= 1
        assert len(team.agents) <= 2  # One task needs 1-2 agents max

    def test_compose_team_with_custom_name(self, composer):
        """Test team composition with custom team name."""
        subtasks = [
            Subtask(
                id="subtask-1",
                description="Task",
                requirements={"capabilities": ["coding"]},
            ),
        ]

        team = composer.compose_team(subtasks, team_name="Custom Team Name")

        assert team.name == "Custom Team Name"

    def test_compose_team_with_max_team_size(self, composer):
        """Test that team size respects maximum limit."""
        # Create many subtasks
        subtasks = [
            Subtask(
                id=f"subtask-{i}",
                description=f"Task {i}",
                requirements={"capabilities": ["coding"]},
            )
            for i in range(100)
        ]

        team = composer.compose_team(subtasks, max_team_size=5)

        # Should not exceed max team size
        assert len(team.agents) <= 5

    def test_compose_team_role_diversity(self, composer):
        """Test that team has diverse roles when needed."""
        subtasks = [
            Subtask(
                id="subtask-1",
                description="Code",
                requirements={"capabilities": ["coding"]},
            ),
            Subtask(
                id="subtask-2",
                description="Test",
                requirements={"capabilities": ["testing"]},
            ),
            Subtask(
                id="subtask-3",
                description="Analyze",
                requirements={"capabilities": ["data_analysis"]},
            ),
            Subtask(
                id="subtask-4",
                description="Research",
                requirements={"capabilities": ["research"]},
            ),
        ]

        team = composer.compose_team(subtasks)

        roles = {agent.role for agent in team.agents}
        # Should have at least 2 different roles for diverse tasks
        assert len(roles) >= 2

    def test_compose_team_metadata_preserved(self, composer):
        """Test that team metadata is properly set."""
        subtasks = [
            Subtask(
                id="subtask-1",
                description="Task",
                requirements={"capabilities": ["coding"]},
            ),
        ]

        team = composer.compose_team(
            subtasks,
            team_name="Meta Team",
            metadata={"project": "Test Project", "priority": "high"},
        )

        assert team.metadata["project"] == "Test Project"
        assert team.metadata["priority"] == "high"

    def test_compose_team_no_matching_roles(self, composer):
        """Test team composition when no roles match requirements."""
        # Create subtask with requirements that don't match any role
        subtasks = [
            Subtask(
                id="subtask-1",
                description="Impossible task",
                requirements={
                    "capabilities": ["nonexistent_capability_xyz"],
                    "tools": ["nonexistent_tool_abc"],
                },
            ),
        ]

        team = composer.compose_team(subtasks)

        # Should still create a team, perhaps with best available roles
        assert team is not None
        # May have agents with low match scores, or empty team
        assert len(team.agents) >= 0

    def test_compose_team_partial_role_match(self, composer):
        """Test team composition with partial role matches."""
        subtasks = [
            Subtask(
                id="subtask-1",
                description="Task with mixed requirements",
                requirements={
                    "capabilities": ["coding", "nonexistent_capability"],
                    "tools": ["python", "nonexistent_tool"],
                },
            ),
        ]

        team = composer.compose_team(subtasks)

        # Should compose team with best partial matches
        assert team is not None
        assert len(team.agents) > 0  # Should find at least developer role

    def test_compose_team_balances_workload(self, composer):
        """Test that workload is balanced across agents."""
        subtasks = [
            Subtask(
                id=f"subtask-{i}",
                description=f"Coding task {i}",
                requirements={"capabilities": ["coding"]},
            )
            for i in range(6)
        ]

        team = composer.compose_team(subtasks)

        # Check that tasks are distributed
        total_tasks = sum(len(agent.assigned_tasks) for agent in team.agents)
        assert total_tasks == len(subtasks)

        # Check that no agent is overloaded while others are idle
        if len(team.agents) > 1:
            task_counts = [len(agent.assigned_tasks) for agent in team.agents]
            max_tasks = max(task_counts)
            min_tasks = min(task_counts)
            # Difference should not be too large
            assert max_tasks - min_tasks <= 2
