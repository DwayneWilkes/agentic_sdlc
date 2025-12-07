"""Tests for OrchestratorWrapper - smart dispatcher for NL requests."""


from src.core.task_parser import ParsedTask
from src.models.enums import TaskType
from src.orchestrator.wrapper import (
    ComplexityLevel,
    ExecutionMode,
    ExecutionResult,
    OrchestratorWrapper,
)


class TestComplexityAssessment:
    """Test complexity assessment logic."""

    def test_assess_simple_task_single_step(self):
        """Simple task with single goal should be assessed as SIMPLE."""
        wrapper = OrchestratorWrapper()
        parsed = ParsedTask(
            goal="Fix the typo in README.md",
            task_type=TaskType.SOFTWARE,
            raw_description="Fix the typo in README.md",
        )

        assessment = wrapper.assess_complexity(parsed)

        assert assessment.level == ComplexityLevel.SIMPLE
        assert assessment.reasoning is not None
        assert "single" in assessment.reasoning.lower()

    def test_assess_complex_task_multiple_requirements(self):
        """Task with multiple requirements should be assessed as COMPLEX."""
        wrapper = OrchestratorWrapper()
        parsed = ParsedTask(
            goal="Build a REST API with authentication, user management, and data export",
            task_type=TaskType.SOFTWARE,
            constraints={
                "technology": ["OAuth2", "PostgreSQL", "FastAPI"],
                "quality": ["test coverage >= 90%", "API documentation"],
            },
            success_criteria=[
                "Users can register and login",
                "Admin can manage users",
                "Data can be exported to CSV/JSON",
                "All endpoints documented",
            ],
            raw_description="Build a REST API...",
        )

        assessment = wrapper.assess_complexity(parsed)

        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.estimated_subtasks >= 3
        assert "multiple" in assessment.reasoning.lower()

    def test_assess_medium_complexity_few_requirements(self):
        """Task with a few related steps should be assessed as MEDIUM."""
        wrapper = OrchestratorWrapper()
        parsed = ParsedTask(
            goal="Add logging to the authentication module",
            task_type=TaskType.SOFTWARE,
            success_criteria=[
                "All auth functions log entry/exit",
                "Errors are logged with context",
                "Log levels are configurable",
            ],
            raw_description="Add logging to the authentication module",
        )

        assessment = wrapper.assess_complexity(parsed)

        assert assessment.level in (ComplexityLevel.MEDIUM, ComplexityLevel.SIMPLE)

    def test_research_task_is_medium_complexity(self):
        """Research tasks should typically be medium complexity."""
        wrapper = OrchestratorWrapper()
        parsed = ParsedTask(
            goal="Research and compare Python async frameworks",
            task_type=TaskType.RESEARCH,
            success_criteria=[
                "Compare performance characteristics",
                "Evaluate ecosystem maturity",
                "Recommend best fit for our use case",
            ],
            raw_description="Research async frameworks",
        )

        assessment = wrapper.assess_complexity(parsed)

        assert assessment.level in (ComplexityLevel.MEDIUM, ComplexityLevel.COMPLEX)


class TestOrchestratorWrapperModes:
    """Test execution mode selection."""

    def test_simple_task_uses_single_agent_mode(self):
        """Simple tasks should use single agent mode."""
        wrapper = OrchestratorWrapper()
        parsed = ParsedTask(
            goal="Update copyright year in all Python files",
            task_type=TaskType.SOFTWARE,
            raw_description="Update copyright year",
        )

        mode = wrapper.select_execution_mode(parsed)

        assert mode == ExecutionMode.SINGLE_AGENT

    def test_complex_task_uses_coordinated_team_mode(self):
        """Complex tasks should use coordinated team mode."""
        wrapper = OrchestratorWrapper()
        parsed = ParsedTask(
            goal="Implement complete OAuth2 authentication system",
            task_type=TaskType.SOFTWARE,
            success_criteria=[
                "Authorization server",
                "Token management",
                "Client integration",
                "Security testing",
            ],
            raw_description="Implement OAuth2 system",
        )

        mode = wrapper.select_execution_mode(parsed)

        assert mode == ExecutionMode.COORDINATED_TEAM


class TestOrchestratorWrapperProcessRequest:
    """Test the main process_request flow."""

    def test_process_simple_request_returns_result(self):
        """Processing a simple request should return an ExecutionResult."""
        wrapper = OrchestratorWrapper(dry_run=True)  # Don't actually spawn agents
        request = "Fix the typo in README.md on line 42"

        result = wrapper.process_request(request)

        assert isinstance(result, ExecutionResult)
        assert result.request == request
        assert result.parsed_task is not None
        assert result.mode == ExecutionMode.SINGLE_AGENT
        assert result.success is not None

    def test_process_complex_request_decomposes_task(self):
        """Processing a complex request should decompose into subtasks."""
        wrapper = OrchestratorWrapper(dry_run=True)
        request = (
            "Build a user authentication system with OAuth2, "
            "including login, registration, password reset, and admin dashboard"
        )

        result = wrapper.process_request(request)

        assert isinstance(result, ExecutionResult)
        assert result.mode == ExecutionMode.COORDINATED_TEAM
        assert result.decomposition is not None
        assert result.decomposition.dependency_graph.node_count() >= 3  # Multiple subtasks

    def test_process_request_with_ambiguities_includes_clarifications(self):
        """Request with ambiguities should include clarification requests."""
        wrapper = OrchestratorWrapper(dry_run=True)
        request = "Make the app faster"

        result = wrapper.process_request(request)

        assert result.clarifications is not None
        assert len(result.clarifications) > 0
        assert any("faster" in c.lower() for c in result.clarifications)

    def test_process_request_extracts_constraints(self):
        """Request with constraints should extract them properly."""
        wrapper = OrchestratorWrapper(dry_run=True)
        request = (
            "Implement user authentication using JWT tokens. "
            "Must use PostgreSQL for storage. "
            "Target completion: 2 days. "
            "Test coverage must be >= 85%."
        )

        result = wrapper.process_request(request)

        assert result.parsed_task.constraints is not None
        # Should have extracted technology, time, and quality constraints


class TestOrchestratorWrapperIntegration:
    """Test integration with TaskParser, TaskDecomposer, RoleRegistry."""

    def test_uses_task_parser_for_parsing(self):
        """Wrapper should use TaskParser to parse requests."""
        wrapper = OrchestratorWrapper(dry_run=True)
        request = "Build a REST API for user management"

        result = wrapper.process_request(request)

        assert result.parsed_task.task_type == TaskType.SOFTWARE
        assert "REST API" in result.parsed_task.goal or "api" in result.parsed_task.goal.lower()

    def test_uses_task_decomposer_for_complex_tasks(self):
        """Wrapper should use TaskDecomposer for complex tasks."""
        wrapper = OrchestratorWrapper(dry_run=True)
        request = (
            "Create a full-stack app with React frontend, "
            "FastAPI backend, PostgreSQL database, "
            "and Docker deployment configuration"
        )

        result = wrapper.process_request(request)

        # Should have decomposed into multiple subtasks
        if result.mode == ExecutionMode.COORDINATED_TEAM:
            assert result.decomposition is not None
            assert result.decomposition.dependency_graph.node_count() >= 3

    def test_dry_run_does_not_spawn_agents(self):
        """In dry_run mode, no agents should be spawned."""
        wrapper = OrchestratorWrapper(dry_run=True)
        request = "Fix all linting errors"

        result = wrapper.process_request(request)

        # Should complete successfully without actually running agents
        assert result is not None
        assert result.success is not None


class TestExecutionResultDataclass:
    """Test ExecutionResult data structure."""

    def test_execution_result_has_required_fields(self):
        """ExecutionResult should have all required fields."""
        parsed = ParsedTask(
            goal="Test goal",
            task_type=TaskType.SOFTWARE,
            raw_description="Test",
        )

        result = ExecutionResult(
            request="Test request",
            parsed_task=parsed,
            mode=ExecutionMode.SINGLE_AGENT,
            success=True,
        )

        assert result.request == "Test request"
        assert result.parsed_task == parsed
        assert result.mode == ExecutionMode.SINGLE_AGENT
        assert result.success is True

    def test_execution_result_optional_fields_default_none(self):
        """Optional fields should default to None."""
        parsed = ParsedTask(
            goal="Test goal",
            task_type=TaskType.SOFTWARE,
            raw_description="Test",
        )

        result = ExecutionResult(
            request="Test request",
            parsed_task=parsed,
            mode=ExecutionMode.SINGLE_AGENT,
            success=True,
        )

        assert result.decomposition is None
        assert result.clarifications is None
        assert result.error is None


class TestComplexityLevelEnum:
    """Test ComplexityLevel enum."""

    def test_complexity_levels_exist(self):
        """All expected complexity levels should exist."""
        assert ComplexityLevel.SIMPLE
        assert ComplexityLevel.MEDIUM
        assert ComplexityLevel.COMPLEX

    def test_complexity_levels_comparable(self):
        """Complexity levels should be comparable (if implemented as ordered enum)."""
        # This test might need adjustment based on implementation
        assert ComplexityLevel.SIMPLE != ComplexityLevel.COMPLEX


class TestExecutionModeEnum:
    """Test ExecutionMode enum."""

    def test_execution_modes_exist(self):
        """All expected execution modes should exist."""
        assert ExecutionMode.SINGLE_AGENT
        assert ExecutionMode.COORDINATED_TEAM
