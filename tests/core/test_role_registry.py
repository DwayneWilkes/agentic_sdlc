"""Tests for Agent Role Registry."""

import pytest

from src.core.role_registry import RoleMatcher, RoleRegistry
from src.models.agent import AgentRole


class TestAgentRole:
    """Test AgentRole model."""

    def test_role_creation_minimal(self):
        """Test creating a role with minimal fields."""
        role = AgentRole(
            name="developer",
            description="Software developer",
            capabilities=[],
            tools=[],
            domain_knowledge=[],
        )
        assert role.name == "developer"
        assert role.description == "Software developer"
        assert role.capabilities == []
        assert role.tools == []
        assert role.domain_knowledge == []
        assert role.metadata == {}

    def test_role_creation_full(self):
        """Test creating a role with all fields."""
        role = AgentRole(
            name="senior_developer",
            description="Senior software developer",
            capabilities=["python", "testing", "architecture"],
            tools=["pytest", "mypy", "git"],
            domain_knowledge=["web_development", "microservices", "databases"],
            metadata={"experience_level": "senior", "certifications": ["AWS"]},
        )
        assert role.name == "senior_developer"
        assert len(role.capabilities) == 3
        assert "python" in role.capabilities
        assert len(role.tools) == 3
        assert "pytest" in role.tools
        assert len(role.domain_knowledge) == 3
        assert "web_development" in role.domain_knowledge
        assert role.metadata["experience_level"] == "senior"

    def test_role_with_metadata(self):
        """Test role with custom metadata."""
        role = AgentRole(
            name="researcher",
            description="Research analyst",
            capabilities=["data_analysis", "literature_review"],
            tools=["jupyter", "pandas", "scikit-learn"],
            domain_knowledge=["machine_learning", "statistics"],
            metadata={
                "research_areas": ["NLP", "CV"],
                "publications": 15,
                "h_index": 12,
            },
        )
        assert role.metadata["research_areas"] == ["NLP", "CV"]
        assert role.metadata["publications"] == 15


class TestRoleRegistry:
    """Test RoleRegistry functionality."""

    def test_registry_creation(self):
        """Test creating an empty registry."""
        registry = RoleRegistry()
        assert registry is not None
        assert len(registry.list_roles()) == 0

    def test_register_role(self):
        """Test registering a role."""
        registry = RoleRegistry()
        role = AgentRole(
            name="developer",
            description="Software developer",
            capabilities=["coding"],
            tools=["git"],
            domain_knowledge=["software"],
        )
        registry.register_role(role)
        assert len(registry.list_roles()) == 1
        assert "developer" in [r.name for r in registry.list_roles()]

    def test_register_multiple_roles(self):
        """Test registering multiple roles."""
        registry = RoleRegistry()
        roles = [
            AgentRole(
                name="developer",
                description="Developer",
                capabilities=["coding"],
                tools=["git"],
                domain_knowledge=["software"],
            ),
            AgentRole(
                name="tester",
                description="Tester",
                capabilities=["testing"],
                tools=["pytest"],
                domain_knowledge=["qa"],
            ),
        ]
        for role in roles:
            registry.register_role(role)
        assert len(registry.list_roles()) == 2

    def test_get_role_by_name(self):
        """Test retrieving a role by name."""
        registry = RoleRegistry()
        role = AgentRole(
            name="analyst",
            description="Data analyst",
            capabilities=["analysis"],
            tools=["pandas"],
            domain_knowledge=["data"],
        )
        registry.register_role(role)
        retrieved = registry.get_role("analyst")
        assert retrieved is not None
        assert retrieved.name == "analyst"
        assert retrieved.description == "Data analyst"

    def test_get_nonexistent_role(self):
        """Test getting a role that doesn't exist."""
        registry = RoleRegistry()
        result = registry.get_role("nonexistent")
        assert result is None

    def test_register_duplicate_role_raises_error(self):
        """Test that registering duplicate role names raises an error."""
        registry = RoleRegistry()
        role1 = AgentRole(
            name="developer",
            description="First developer",
            capabilities=["coding"],
            tools=["git"],
            domain_knowledge=["software"],
        )
        role2 = AgentRole(
            name="developer",
            description="Second developer",
            capabilities=["testing"],
            tools=["pytest"],
            domain_knowledge=["qa"],
        )
        registry.register_role(role1)
        with pytest.raises(ValueError, match="already registered"):
            registry.register_role(role2)

    def test_create_standard_registry(self):
        """Test creating a registry with standard roles."""
        registry = RoleRegistry.create_standard_registry()
        roles = registry.list_roles()
        assert len(roles) >= 5  # At least Developer, Researcher, Analyst, Tester, Reviewer
        role_names = [r.name for r in roles]
        assert "developer" in role_names
        assert "researcher" in role_names
        assert "analyst" in role_names
        assert "tester" in role_names
        assert "reviewer" in role_names

    def test_standard_developer_role(self):
        """Test the standard developer role."""
        registry = RoleRegistry.create_standard_registry()
        dev = registry.get_role("developer")
        assert dev is not None
        assert "python" in dev.capabilities or "coding" in dev.capabilities
        assert len(dev.tools) > 0
        assert len(dev.domain_knowledge) > 0

    def test_standard_researcher_role(self):
        """Test the standard researcher role."""
        registry = RoleRegistry.create_standard_registry()
        researcher = registry.get_role("researcher")
        assert researcher is not None
        assert "research" in researcher.capabilities or "analysis" in researcher.capabilities
        assert len(researcher.tools) > 0

    def test_standard_analyst_role(self):
        """Test the standard analyst role."""
        registry = RoleRegistry.create_standard_registry()
        analyst = registry.get_role("analyst")
        assert analyst is not None
        assert "analysis" in analyst.capabilities or "data_analysis" in analyst.capabilities

    def test_standard_tester_role(self):
        """Test the standard tester role."""
        registry = RoleRegistry.create_standard_registry()
        tester = registry.get_role("tester")
        assert tester is not None
        assert "testing" in tester.capabilities or "qa" in tester.capabilities

    def test_standard_reviewer_role(self):
        """Test the standard reviewer role."""
        registry = RoleRegistry.create_standard_registry()
        reviewer = registry.get_role("reviewer")
        assert reviewer is not None
        assert "review" in reviewer.capabilities or "code_review" in reviewer.capabilities


class TestRoleMatcher:
    """Test RoleMatcher functionality."""

    def test_matcher_creation(self):
        """Test creating a matcher."""
        registry = RoleRegistry()
        matcher = RoleMatcher(registry)
        assert matcher is not None

    def test_exact_capability_match(self):
        """Test matching with exact capability."""
        registry = RoleRegistry()
        role = AgentRole(
            name="python_dev",
            description="Python developer",
            capabilities=["python", "testing"],
            tools=["pytest"],
            domain_knowledge=["web"],
        )
        registry.register_role(role)
        matcher = RoleMatcher(registry)

        requirements = {"capabilities": ["python"]}
        matches = matcher.find_matching_roles(requirements)
        assert len(matches) > 0
        assert matches[0]["role"].name == "python_dev"
        assert matches[0]["score"] > 0

    def test_tool_match(self):
        """Test matching based on tools."""
        registry = RoleRegistry()
        role = AgentRole(
            name="tester",
            description="Test engineer",
            capabilities=["testing"],
            tools=["pytest", "selenium", "jest"],
            domain_knowledge=["qa"],
        )
        registry.register_role(role)
        matcher = RoleMatcher(registry)

        requirements = {"tools": ["pytest"]}
        matches = matcher.find_matching_roles(requirements)
        assert len(matches) > 0
        assert matches[0]["role"].name == "tester"

    def test_domain_knowledge_match(self):
        """Test matching based on domain knowledge."""
        registry = RoleRegistry()
        role = AgentRole(
            name="ml_engineer",
            description="ML engineer",
            capabilities=["machine_learning"],
            tools=["pytorch", "tensorflow"],
            domain_knowledge=["deep_learning", "nlp", "computer_vision"],
        )
        registry.register_role(role)
        matcher = RoleMatcher(registry)

        requirements = {"domain_knowledge": ["nlp"]}
        matches = matcher.find_matching_roles(requirements)
        assert len(matches) > 0
        assert matches[0]["role"].name == "ml_engineer"

    def test_multiple_criteria_match(self):
        """Test matching with multiple criteria."""
        registry = RoleRegistry()
        role = AgentRole(
            name="full_stack",
            description="Full stack developer",
            capabilities=["frontend", "backend", "devops"],
            tools=["react", "fastapi", "docker"],
            domain_knowledge=["web_development", "microservices"],
        )
        registry.register_role(role)
        matcher = RoleMatcher(registry)

        requirements = {
            "capabilities": ["frontend", "backend"],
            "tools": ["docker"],
            "domain_knowledge": ["web_development"],
        }
        matches = matcher.find_matching_roles(requirements)
        assert len(matches) > 0
        assert matches[0]["role"].name == "full_stack"
        # Should have high score for matching multiple criteria
        assert matches[0]["score"] > 0.5

    def test_partial_match(self):
        """Test partial matching (not all requirements met)."""
        registry = RoleRegistry()
        role = AgentRole(
            name="backend_dev",
            description="Backend developer",
            capabilities=["backend"],
            tools=["fastapi"],
            domain_knowledge=["databases"],
        )
        registry.register_role(role)
        matcher = RoleMatcher(registry)

        requirements = {
            "capabilities": ["backend", "frontend"],  # Only backend matches
            "tools": ["fastapi"],
        }
        matches = matcher.find_matching_roles(requirements)
        assert len(matches) > 0
        # Score should be less than perfect match
        assert 0 < matches[0]["score"] < 1.0

    def test_no_match(self):
        """Test when no roles match requirements."""
        registry = RoleRegistry()
        role = AgentRole(
            name="developer",
            description="Developer",
            capabilities=["python"],
            tools=["git"],
            domain_knowledge=["software"],
        )
        registry.register_role(role)
        matcher = RoleMatcher(registry)

        requirements = {"capabilities": ["quantum_computing"]}
        matches = matcher.find_matching_roles(requirements)
        # Either no matches or very low scores
        assert len(matches) == 0 or matches[0]["score"] < 0.1

    def test_match_ranking(self):
        """Test that matches are ranked by score."""
        registry = RoleRegistry()
        roles = [
            AgentRole(
                name="expert",
                description="Expert",
                capabilities=["python", "rust", "go"],
                tools=["pytest", "cargo", "gotest"],
                domain_knowledge=["systems", "web", "cli"],
            ),
            AgentRole(
                name="intermediate",
                description="Intermediate",
                capabilities=["python"],
                tools=["pytest"],
                domain_knowledge=["web"],
            ),
            AgentRole(
                name="beginner",
                description="Beginner",
                capabilities=["scripting"],
                tools=["bash"],
                domain_knowledge=["automation"],
            ),
        ]
        for role in roles:
            registry.register_role(role)
        matcher = RoleMatcher(registry)

        requirements = {
            "capabilities": ["python"],
            "tools": ["pytest"],
            "domain_knowledge": ["web"],
        }
        matches = matcher.find_matching_roles(requirements)
        assert len(matches) >= 2
        # Should be sorted by descending score
        for i in range(len(matches) - 1):
            assert matches[i]["score"] >= matches[i + 1]["score"]

    def test_empty_requirements(self):
        """Test matching with empty requirements."""
        registry = RoleRegistry()
        role = AgentRole(
            name="generalist",
            description="Generalist",
            capabilities=["general"],
            tools=["basic"],
            domain_knowledge=["general"],
        )
        registry.register_role(role)
        matcher = RoleMatcher(registry)

        requirements = {}
        matches = matcher.find_matching_roles(requirements)
        # Should return all roles with neutral scores
        assert len(matches) > 0

    def test_match_minimum_score_filter(self):
        """Test filtering matches by minimum score."""
        registry = RoleRegistry()
        roles = [
            AgentRole(
                name="perfect_match",
                description="Perfect",
                capabilities=["python", "testing"],
                tools=["pytest"],
                domain_knowledge=["qa"],
            ),
            AgentRole(
                name="poor_match",
                description="Poor",
                capabilities=["java"],
                tools=["junit"],
                domain_knowledge=["android"],
            ),
        ]
        for role in roles:
            registry.register_role(role)
        matcher = RoleMatcher(registry)

        requirements = {"capabilities": ["python"]}
        matches = matcher.find_matching_roles(requirements, min_score=0.5)
        # Should only return good matches
        assert all(m["score"] >= 0.5 for m in matches)

    def test_match_returns_role_and_score(self):
        """Test that matches return both role and score."""
        registry = RoleRegistry()
        role = AgentRole(
            name="dev",
            description="Developer",
            capabilities=["coding"],
            tools=["git"],
            domain_knowledge=["software"],
        )
        registry.register_role(role)
        matcher = RoleMatcher(registry)

        requirements = {"capabilities": ["coding"]}
        matches = matcher.find_matching_roles(requirements)
        assert len(matches) > 0
        match = matches[0]
        assert "role" in match
        assert "score" in match
        assert isinstance(match["role"], AgentRole)
        assert isinstance(match["score"], (int, float))
        assert 0 <= match["score"] <= 1.0

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        registry = RoleRegistry()
        role = AgentRole(
            name="developer",
            description="Developer",
            capabilities=["Python", "JavaScript"],
            tools=["Git"],
            domain_knowledge=["WebDevelopment"],
        )
        registry.register_role(role)
        matcher = RoleMatcher(registry)

        requirements = {"capabilities": ["python"]}
        matches = matcher.find_matching_roles(requirements)
        assert len(matches) > 0
        assert matches[0]["role"].name == "developer"
