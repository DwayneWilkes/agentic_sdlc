"""Agent Role Registry for managing and matching agent roles."""

from typing import Any, cast

from src.models.agent import AgentRole


class RoleRegistry:
    """
    Registry for managing agent role definitions.

    The RoleRegistry stores and manages available agent roles, providing
    methods to register new roles and retrieve existing ones.
    """

    def __init__(self) -> None:
        """Initialize an empty role registry."""
        self._roles: dict[str, AgentRole] = {}

    def register_role(self, role: AgentRole) -> None:
        """
        Register a new role in the registry.

        Args:
            role: The AgentRole to register

        Raises:
            ValueError: If a role with the same name is already registered
        """
        if role.name in self._roles:
            raise ValueError(
                f"Role '{role.name}' is already registered. "
                "Cannot register duplicate role names."
            )
        self._roles[role.name] = role

    def get_role(self, name: str) -> AgentRole | None:
        """
        Retrieve a role by name.

        Args:
            name: The name of the role to retrieve

        Returns:
            The AgentRole if found, None otherwise
        """
        return self._roles.get(name)

    def list_roles(self) -> list[AgentRole]:
        """
        Get a list of all registered roles.

        Returns:
            List of all AgentRole objects in the registry
        """
        return list(self._roles.values())

    @classmethod
    def create_standard_registry(cls) -> "RoleRegistry":
        """
        Create a registry pre-populated with standard agent roles.

        Returns:
            A RoleRegistry containing standard roles (Developer, Researcher,
            Analyst, Tester, Reviewer)
        """
        registry = cls()

        # Developer role
        developer = AgentRole(
            name="developer",
            description="Software developer with coding and implementation skills",
            capabilities=[
                "coding",
                "implementation",
                "debugging",
                "version_control",
                "documentation",
            ],
            tools=[
                "git",
                "python",
                "pytest",
                "mypy",
                "black",
                "ruff",
                "docker",
            ],
            domain_knowledge=[
                "software_engineering",
                "algorithms",
                "data_structures",
                "design_patterns",
                "testing",
                "ci_cd",
            ],
            metadata={
                "experience_level": "intermediate",
                "primary_languages": ["python", "javascript", "typescript"],
            },
        )

        # Researcher role
        researcher = AgentRole(
            name="researcher",
            description="Research analyst with investigation and analysis skills",
            capabilities=[
                "research",
                "literature_review",
                "data_collection",
                "analysis",
                "synthesis",
                "documentation",
            ],
            tools=[
                "web_search",
                "pdf_parser",
                "jupyter",
                "pandas",
                "matplotlib",
                "notion",
            ],
            domain_knowledge=[
                "research_methodology",
                "data_analysis",
                "statistics",
                "academic_writing",
                "information_retrieval",
            ],
            metadata={
                "research_areas": ["technology", "science", "business"],
            },
        )

        # Analyst role
        analyst = AgentRole(
            name="analyst",
            description="Data analyst with analytical and visualization skills",
            capabilities=[
                "data_analysis",
                "statistical_analysis",
                "data_visualization",
                "pattern_recognition",
                "reporting",
                "insight_generation",
            ],
            tools=[
                "pandas",
                "numpy",
                "matplotlib",
                "seaborn",
                "jupyter",
                "sql",
                "excel",
            ],
            domain_knowledge=[
                "statistics",
                "data_science",
                "business_intelligence",
                "data_warehousing",
                "visualization_design",
            ],
            metadata={
                "specializations": ["quantitative_analysis", "data_visualization"],
            },
        )

        # Tester role
        tester = AgentRole(
            name="tester",
            description="Quality assurance engineer with testing expertise",
            capabilities=[
                "testing",
                "test_planning",
                "test_automation",
                "bug_detection",
                "quality_assurance",
                "test_documentation",
            ],
            tools=[
                "pytest",
                "unittest",
                "selenium",
                "jest",
                "cypress",
                "postman",
                "jira",
            ],
            domain_knowledge=[
                "qa_methodology",
                "test_driven_development",
                "integration_testing",
                "e2e_testing",
                "performance_testing",
                "security_testing",
            ],
            metadata={
                "test_types": ["unit", "integration", "e2e", "performance"],
            },
        )

        # Reviewer role
        reviewer = AgentRole(
            name="reviewer",
            description="Code reviewer with quality and best practices expertise",
            capabilities=[
                "code_review",
                "quality_assessment",
                "best_practices_enforcement",
                "mentoring",
                "documentation_review",
                "architecture_review",
            ],
            tools=[
                "git",
                "github",
                "sonarqube",
                "eslint",
                "pylint",
                "ruff",
            ],
            domain_knowledge=[
                "code_quality",
                "design_patterns",
                "security_best_practices",
                "performance_optimization",
                "maintainability",
                "readability",
            ],
            metadata={
                "review_focus": ["security", "performance", "maintainability"],
            },
        )

        # Register all standard roles
        for role in [developer, researcher, analyst, tester, reviewer]:
            registry.register_role(role)

        return registry


class RoleMatcher:
    """
    Matches task requirements to appropriate agent roles.

    The RoleMatcher analyzes task requirements and finds the best matching
    agent roles based on capabilities, tools, and domain knowledge.
    """

    def __init__(self, registry: RoleRegistry):
        """
        Initialize the role matcher with a registry.

        Args:
            registry: The RoleRegistry to use for matching
        """
        self._registry = registry

    def find_matching_roles(
        self,
        requirements: dict[str, Any],
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Find roles that match the given requirements.

        Args:
            requirements: Dictionary containing:
                - capabilities: List of required capabilities
                - tools: List of required tools
                - domain_knowledge: List of required domain knowledge
            min_score: Minimum match score (0.0 to 1.0) to include in results

        Returns:
            List of dicts with keys:
                - role: The matching AgentRole
                - score: Match score (0.0 to 1.0)
            Sorted by score in descending order
        """
        required_capabilities = [
            c.lower() for c in requirements.get("capabilities", [])
        ]
        required_tools = [t.lower() for t in requirements.get("tools", [])]
        required_knowledge = [
            k.lower() for k in requirements.get("domain_knowledge", [])
        ]

        matches = []
        all_roles = self._registry.list_roles()

        for role in all_roles:
            score = self._calculate_match_score(
                role,
                required_capabilities,
                required_tools,
                required_knowledge,
            )

            if score >= min_score:
                matches.append({"role": role, "score": score})

        # Sort by score in descending order
        matches.sort(key=lambda x: cast(float, x["score"]), reverse=True)

        return matches

    def _calculate_match_score(
        self,
        role: AgentRole,
        required_capabilities: list[str],
        required_tools: list[str],
        required_knowledge: list[str],
    ) -> float:
        """
        Calculate match score between a role and requirements.

        Args:
            role: The AgentRole to score
            required_capabilities: Required capabilities (lowercase)
            required_tools: Required tools (lowercase)
            required_knowledge: Required domain knowledge (lowercase)

        Returns:
            Match score between 0.0 and 1.0
        """
        # Convert role attributes to lowercase for case-insensitive comparison
        role_capabilities = [c.lower() for c in role.capabilities]
        role_tools = [t.lower() for t in role.tools]
        role_knowledge = [k.lower() for k in role.domain_knowledge]

        # If no requirements specified, return neutral score
        total_requirements = (
            len(required_capabilities) + len(required_tools) + len(required_knowledge)
        )
        if total_requirements == 0:
            return 0.5

        # Count matches
        capability_matches = sum(
            1 for cap in required_capabilities if cap in role_capabilities
        )
        tool_matches = sum(1 for tool in required_tools if tool in role_tools)
        knowledge_matches = sum(
            1 for know in required_knowledge if know in role_knowledge
        )

        total_matches = capability_matches + tool_matches + knowledge_matches

        # Calculate score as percentage of requirements met
        score = total_matches / total_requirements

        return score
